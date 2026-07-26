import 'package:dio/dio.dart';

import '../../api/api_exception.dart';
import '../../models/place_search_models.dart';
import '../../models/route_planning_models.dart';
import '../../models/transport_mode.dart';
import '../../models/travel_models.dart';
import '../../services/trip_session_service.dart';
import '../plan_repository.dart';

/// chiwawa_backend를 통해 Modal Route Planner를 호출하는 구현체.
/// POST /api/v1/trips/{trip_id}/route-optimizations
class ApiPlanRepository implements PlanRepository {
  const ApiPlanRepository({required this.dio, required this.tripIdStore});

  final Dio dio;
  final TripIdStore tripIdStore;

  @override
  List<String> get defaultSelectedPlaces => const [];

  @override
  Future<WantedPlaceRecord> saveWantedPlace(
    PlanRoutePlaceInput place,
  ) async {
    final tripId = await _requireTripId();
    try {
      final response = await dio.post<Map<String, Object?>>(
        '/api/v1/trips/$tripId/wanted-places',
        data: {
          if (place.providerPlaceId != null)
            'provider_place_id': place.providerPlaceId,
          'name': place.name,
          if (place.latitude != null) 'latitude': place.latitude,
          if (place.longitude != null) 'longitude': place.longitude,
        },
      );
      return WantedPlaceRecord.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      final apiError = ApiException.fromDioException(error);
      if (apiError.isNotFound) {
        await tripIdStore.clear();
        throw const ApiException(
          '현재 선택한 여행이 서버에 없어요. 여행을 다시 선택하거나 만들어 주세요.',
          statusCode: 404,
        );
      }
      throw apiError;
    }
  }

  @override
  Future<RouteOptimizationResult> optimizeRoute(
    RouteOptimizationRequest request,
  ) async {
    final tripId = await _requireTripId();

    try {
      final response = await dio.post<Map<String, Object?>>(
        '/api/v1/trips/$tripId/route-optimizations',
        data: {
          'transport_mode': request.transportMode.backendCode,
          'day_index': request.dayIndex,
          'planned_start_time': request.plannedStartTime,
          'planned_end_time': request.plannedEndTime,
          'max_place_count': request.maxPlaceCount,
          'start': _placePayload(request.startPlace),
          'end': _placePayload(request.endPlace),
          'wanted_place_ids': request.wantedPlaceIds,
          'pace': request.preference.pace.code,
          'include_recommendations': true,
        },
        options: Options(
          sendTimeout: const Duration(seconds: 310),
          receiveTimeout: const Duration(seconds: 310),
        ),
      );
      final json = response.data ?? const {};
      final responseMode = TransportModeMapping.fromBackendCode(
        json['transport_mode'] as String?,
        fallback: request.transportMode,
      );
      final stops = json['stops'] as List<Object?>? ?? const [];
      final rawTimeline = json['timeline'];
      final timeline = rawTimeline is Map
          ? RouteTimeline.fromJson(Map<String, Object?>.from(rawTimeline))
          : null;
      final missingSegments =
          (json['missing_segments'] as List<Object?>? ?? const [])
              .whereType<String>()
              .toList(growable: false);
      final warnings = (json['warnings'] as List<Object?>? ?? const [])
          .whereType<String>()
          .toList(growable: false);
      if (timeline == null || missingSegments.isNotEmpty) {
        return RouteOptimizationResult.unavailable(
          missingSegments: missingSegments,
          warnings: warnings,
        );
      }
      final timelineStopsById = {
        for (final stop in timeline.timelineStops) stop.placeId: stop,
      };
      final recommendationGroups =
          json['recommendation_groups'] as List<Object?>? ?? const [];
      return RouteOptimizationResult.success(
        places: [
          for (final raw in stops)
            _stopToRoutePlace(
              Map<String, Object?>.from(raw! as Map),
              responseMode,
              timelineStopsById,
            ),
        ],
        timeline: timeline,
        warnings: warnings,
        recommendationGroups: [
          for (final raw in recommendationGroups)
            RouteRecommendationGroup.fromJson(
              Map<String, Object?>.from(raw! as Map),
            ),
        ],
      );
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  @override
  Future<void> confirmRoute(RouteOptimizationResult result) async {
    final timeline = result.timeline;
    if (timeline == null) {
      throw const ApiException('확정할 타임라인이 없어요. 경로를 다시 계산해 주세요.');
    }
    final tripId = await _requireTripId();
    try {
      await dio.post<Map<String, Object?>>(
        '/api/v1/trips/$tripId/route-optimizations/confirm',
        data: {'timeline': timeline.toJson()},
      );
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  Future<String> _requireTripId() async {
    await tripIdStore.restoreCompleted;
    final tripId = tripIdStore.tripId;
    if (tripId == null || tripId.isEmpty) {
      throw const ApiException('여행 정보가 없어요. 여행을 먼저 만들어 주세요.');
    }
    return tripId;
  }

  RoutePlace _stopToRoutePlace(
    Map<String, Object?> json,
    TransportMode transportMode,
    Map<String, RouteTimelineStop> timelineStopsById,
  ) {
    final travelMinutes = (json['estimated_travel_minutes'] as num?)?.toInt();
    final placeId = json['place_id']?.toString() ?? '';
    final timelineStop = timelineStopsById[placeId];
    return RoutePlace(
      placeId: placeId,
      name: json['name'] as String? ?? '',
      duration: timelineStop == null ? '' : '${timelineStop.stayMinutes}분',
      transport: travelMinutes == null
          ? transportMode.label
          : '${transportMode.label} $travelMinutes분',
      category: '',
      travelCost: '',
    );
  }

  Map<String, Object?> _placePayload(PlaceSearchCandidate place) {
    return {
      'place_id': place.providerPlaceId,
      'name': place.name,
      'lat': place.latitude,
      'lng': place.longitude,
    };
  }
}
