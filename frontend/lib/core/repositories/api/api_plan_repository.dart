import 'package:dio/dio.dart';

import '../../models/travel_models.dart';
import '../../services/trip_session_service.dart';
import '../plan_repository.dart';

/// chiwawa_backend 경로 최적화 구현체.
/// POST /api/v1/trips/{trip_id}/route-optimizations
class ApiPlanRepository implements PlanRepository {
  const ApiPlanRepository({required this.dio, required this.tripIdStore});

  final Dio dio;
  final TripIdStore tripIdStore;

  @override
  List<String> get defaultSelectedPlaces =>
      const ['메이지 신궁', '하라주쿠', '오모테산도', '시부야'];

  @override
  Future<List<RoutePlace>> optimizeRoute(
    List<String> places,
    TravelPreference preference,
  ) async {
    // TODO(A9): 경로 최적화가 backend 경유인지 Modal 직접 호출인지 미확정.
    // TODO(C): RouteOptimizationResponse 스키마 확인 후 RoutePlace 매핑.
    throw UnimplementedError('TODO(A9/C): 경로 최적화 연동 방식 확정 후 구현');
  }
}
