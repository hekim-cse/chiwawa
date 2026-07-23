import 'package:dio/dio.dart';

import '../../api/api_exception.dart';
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
  Future<List<RoutePlace>> optimizeRoute(
    List<String> places,
    TravelPreference preference,
    TransportMode transportMode,
  ) async {
    await tripIdStore.restoreCompleted;
    final tripId = tripIdStore.tripId;
    if (tripId == null || tripId.isEmpty) {
      throw const ApiException('여행 정보가 없어요. 여행을 먼저 만들어 주세요.');
    }

    // 백엔드는 트립에 등록된 장소(wanted-places/schedule)를 대상으로 최적화한다.
    // 요청 바디에 전달 가능한 값은 start_place, transport_mode 두 가지뿐이다.
    //
    // NOTE(A9-협의): 화면에서 고른 `places`는 백엔드 계약상 요청에 실리지 않는다.
    //   선택 장소를 먼저 `wanted-places`로 등록하는 흐름이 있어야 최적화 대상에
    //   포함된다(현재 FE 미구현). 등록 흐름/대상 정의를 백엔드와 확정해야 한다.
    // NOTE(A6-협의): `preference`(테마·취향)는 요청 필드가 없어 전달 불가.
    try {
      final response = await dio.post<Map<String, Object?>>(
        '/api/v1/trips/$tripId/route-optimizations',
        data: {'transport_mode': transportMode.backendCode},
      );
      final json = response.data ?? const {};
      final responseMode = TransportModeMapping.fromBackendCode(
        json['transport_mode'] as String?,
        fallback: transportMode,
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

  RoutePlace _stopToRoutePlace(
    Map<String, Object?> json,
    TransportMode transportMode,
  ) {
    final travelMinutes = (json['estimated_travel_minutes'] as num?)?.toInt();
    return RoutePlace(
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
