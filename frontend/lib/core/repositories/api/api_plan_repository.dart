import 'package:dio/dio.dart';

import '../../api/api_exception.dart';
import '../../models/route_planning_models.dart';
import '../../models/transport_mode.dart';
import '../../models/travel_models.dart';
import '../../services/trip_session_service.dart';
import '../plan_repository.dart';

/// chiwawa_backend 경로 최적화 구현체.
/// POST /api/v1/trips/{trip_id}/route-optimizations
///
/// 계약(backend/src/chiwawa_backend/schemas/plans.py):
///   요청  RouteOptimizationRequest { start_place?: str, transport_mode = "transit" }
///   응답  RouteOptimizationResponse { trip_id, transport_mode,
///          stops:[{ order, place_id, name, estimated_travel_minutes }],
///          total_estimated_minutes }
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
          'name': place.name,
          if (place.latitude != null) 'latitude': place.latitude,
          if (place.longitude != null) 'longitude': place.longitude,
        },
      );
      return WantedPlaceRecord.fromJson(response.data ?? const {});
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  @override
  Future<List<RoutePlace>> optimizeRoute(
    RouteOptimizationRequest request,
  ) async {
    final tripId = await _requireTripId();

    // 선택 장소는 이 호출 전에 wanted-place로 저장하고 반환 ID를 보존한다.
    // 선택 ID 목록과 days[]는 Swagger가 확정될 때 요청 바디에 연결한다.
    try {
      final response = await dio.post<Map<String, Object?>>(
        '/api/v1/trips/$tripId/route-optimizations',
        data: {'transport_mode': request.transportMode.backendCode},
      );
      final json = response.data ?? const {};
      final responseMode = TransportModeMapping.fromBackendCode(
        json['transport_mode'] as String?,
        fallback: request.transportMode,
      );
      final stops = json['stops'] as List<Object?>? ?? const [];
      return [
        for (final raw in stops)
          _stopToRoutePlace(
            Map<String, Object?>.from(raw! as Map),
            responseMode,
          ),
      ];
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
  ) {
    final travelMinutes = (json['estimated_travel_minutes'] as num?)?.toInt();
    return RoutePlace(
      placeId: json['place_id']?.toString() ?? '',
      name: json['name'] as String? ?? '',
      // NOTE(협의): 백엔드 stop은 이동시간만 제공하며 체류시간(stay)은 없다.
      duration: '',
      // 구간별 수단은 미제공이므로 응답의 전체 이동수단과 구간 시간을 조합한다.
      transport: travelMinutes == null
          ? transportMode.label
          : '${transportMode.label} $travelMinutes분',
      // NOTE(협의): 백엔드 stop에 장소 카테고리 필드가 없다.
      category: '',
      travelCost: '',
    );
  }
}
