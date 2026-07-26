import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/dio_client.dart';
import '../auth/auth_controller.dart';
import '../env.dart';
import '../mock_data.dart' as mock;
import '../models/route_planning_models.dart';
import '../models/transport_mode.dart';
import '../models/travel_models.dart';
import '../services/trip_session_service.dart';
import 'api/api_plan_repository.dart';

final planRepositoryProvider = Provider<PlanRepository>((ref) {
  ref.watch(authSessionRevisionProvider);
  if (useApiBackend) {
    return ApiPlanRepository(
      dio: ref.watch(dioClientProvider),
      tripIdStore: ref.watch(tripIdStoreProvider),
    );
  }
  return const MockPlanRepository();
});

abstract class PlanRepository {
  /// 화면 초기 표시용 시드(서버 데이터 아님) — Api 구현체도 동일 상수를 반환한다.
  List<String> get defaultSelectedPlaces;

  Future<WantedPlaceRecord> saveWantedPlace(PlanRoutePlaceInput place);

  Future<RouteOptimizationResult> optimizeRoute(
    RouteOptimizationRequest request,
  );

  Future<void> confirmRoute(RouteOptimizationResult result);

  Future<List<ConfirmedRoutePlan>> fetchConfirmedRoutes() async => const [];
}

class MockPlanRepository implements PlanRepository {
  const MockPlanRepository();

  @override
  List<String> get defaultSelectedPlaces =>
      const ['메이지 신궁', '하라주쿠', '오모테산도', '시부야'];

  @override
  Future<WantedPlaceRecord> saveWantedPlace(
    PlanRoutePlaceInput place,
  ) async {
    return WantedPlaceRecord(
      id: place.serverPlaceId ?? 'mock-wanted-${place.localId}',
      name: place.name,
      address: place.address,
      latitude: place.latitude,
      longitude: place.longitude,
    );
  }

  @override
  Future<RouteOptimizationResult> optimizeRoute(
    RouteOptimizationRequest request,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 700));

    // 경로 정보 부족(UNAVAILABLE) 재현: 대중교통은 특정 외곽 구간을 지원하지 못한다.
    // 이동수단별로 결과가 다르다는 점과, 임의 대체 없이 경고로 격리한다는 설계를
    // Mock에서도 보여주기 위한 시나리오다.
    final missingSegments = _missingSegmentsFor(request);
    if (missingSegments.isNotEmpty) {
      return RouteOptimizationResult.unavailable(
        missingSegments: missingSegments,
        warnings: const ['대중교통은 이 구간의 경로 정보를 제공하지 못했어요.'],
      );
    }

    final places = _mockPlacesForRequest(request);
    final timeline = _buildMockTimeline(request, places);
    return RouteOptimizationResult.success(
      places: places,
      timeline: timeline,
      warnings: timeline.warnings,
      recommendationGroups: mock.routeRecommendationGroups,
    );
  }

  @override
  Future<void> confirmRoute(RouteOptimizationResult result) async {
    if (result.timeline == null) {
      throw StateError('확정할 타임라인이 없습니다.');
    }
  }

  @override
  Future<List<ConfirmedRoutePlan>> fetchConfirmedRoutes() async => const [];
}

/// 대중교통으로는 경로를 계산할 수 없는 외곽 구간을 식별한다.
/// 등록 장소 이름에 아래 키워드가 있으면 해당 장소를 누락 구간으로 본다.
/// (Mock 시연에서 이동수단별 결과 차이와 경고 격리를 보여주기 위한 규칙)
const _transitUnsupportedKeywords = ['오다이바', '나리타', '하코네', '가마쿠라'];

List<String> _missingSegmentsFor(RouteOptimizationRequest request) {
  if (request.transportMode != TransportMode.transit) {
    return const [];
  }
  return [
    for (final place in request.places)
      if (_transitUnsupportedKeywords
          .any((keyword) => place.name.contains(keyword)))
        place.name,
  ];
}

List<RoutePlace> _mockPlacesForRequest(RouteOptimizationRequest request) {
  final recommendationInputs = request.places
      .where((place) => place.localId.startsWith('recommendation:'))
      .toList(growable: false);
  final recommendationPlaces = [
    for (final place in recommendationInputs)
      RoutePlace(
        placeId: place.serverPlaceId ?? '',
        name: place.name,
        duration: '40분',
        transport: switch (request.transportMode) {
          TransportMode.walk => '도보 6분',
          TransportMode.drive => '자동차 4분',
          TransportMode.transit => '대중교통 8분',
        },
        category: '추천',
        travelCost: '',
      ),
  ];
  final maxPlaceCount = request.maxPlaceCount;
  final basePlaces = mock.routePlacesFor(request.transportMode);
  final retainedBaseCount = maxPlaceCount == null
      ? basePlaces.length
      : (maxPlaceCount - recommendationPlaces.length).clamp(0, maxPlaceCount);
  final places = [
    ...basePlaces.take(retainedBaseCount),
    ...recommendationPlaces,
  ];
  if (maxPlaceCount == null) return List.unmodifiable(places);
  return places.take(maxPlaceCount).toList(growable: false);
}

RouteTimeline _buildMockTimeline(
  RouteOptimizationRequest request,
  List<RoutePlace> places,
) {
  final date = DateTime(2026);
  final startMinutes = _timeToMinutes(request.plannedStartTime);
  final plannedEndMinutes = _timeToMinutes(request.plannedEndTime);
  var cursor = startMinutes;
  var totalTravelMinutes = 0;
  var totalStayMinutes = 0;
  final stops = <RouteTimelineStop>[
    RouteTimelineStop(
      stopType: 'START',
      placeId: request.startPlace.providerPlaceId,
      name: request.startPlace.name,
      arrivalAt: _isoAt(date, cursor),
      departureAt: _isoAt(date, cursor),
      stayMinutes: 0,
    ),
  ];

  for (var index = 0; index < places.length; index++) {
    final place = places[index];
    final travelMinutes = _minutesIn(place.transport);
    final stayMinutes = _minutesIn(place.duration);
    totalTravelMinutes += travelMinutes;
    totalStayMinutes += stayMinutes;
    cursor += travelMinutes;
    final arrival = cursor;
    cursor += stayMinutes;
    stops.add(
      RouteTimelineStop(
        stopType: 'POI',
        placeId: place.placeId.isEmpty
            ? 'mock-poi-${request.dayIndex}-$index'
            : place.placeId,
        name: place.name,
        arrivalAt: _isoAt(date, arrival),
        departureAt: _isoAt(date, cursor),
        stayMinutes: stayMinutes,
      ),
    );
  }

  stops.add(
    RouteTimelineStop(
      stopType: 'END',
      placeId: request.endPlace.providerPlaceId,
      name: request.endPlace.name,
      arrivalAt: _isoAt(date, cursor),
      departureAt: _isoAt(date, cursor),
      stayMinutes: 0,
    ),
  );
  final exceedsPlannedEnd = cursor > plannedEndMinutes;
  final warnings = exceedsPlannedEnd
      ? const ['예상 종료 시각이 계획한 도착 시간보다 늦어요.']
      : const <String>[];
  return RouteTimeline(
    dayIndex: request.dayIndex,
    travelMode: request.transportMode,
    plannedStartAt: _isoAt(date, startMinutes),
    plannedEndAt: _isoAt(date, plannedEndMinutes),
    actualEndAt: _isoAt(date, cursor),
    totalTravelMinutes: totalTravelMinutes,
    totalStayMinutes: totalStayMinutes,
    timelineStops: stops,
    exceedsPlannedEnd: exceedsPlannedEnd,
    warnings: warnings,
  );
}

int _timeToMinutes(String value) {
  final parts = value.split(':');
  final hour = int.tryParse(parts.first) ?? 0;
  final minute = parts.length > 1 ? int.tryParse(parts[1]) ?? 0 : 0;
  return hour * 60 + minute;
}

int _minutesIn(String value) {
  final match = RegExp(r'(\d+)\s*분').firstMatch(value);
  return int.tryParse(match?.group(1) ?? '') ?? 0;
}

String _isoAt(DateTime date, int totalMinutes) {
  final normalized = totalMinutes.clamp(0, 47 * 60 + 59);
  final value = date.add(Duration(minutes: normalized));
  final year = value.year.toString().padLeft(4, '0');
  final month = value.month.toString().padLeft(2, '0');
  final day = value.day.toString().padLeft(2, '0');
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '$year-$month-${day}T$hour:$minute';
}
