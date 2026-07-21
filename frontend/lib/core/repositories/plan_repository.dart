import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/dio_client.dart';
import '../auth/auth_controller.dart';
import '../env.dart';
import '../mock_data.dart' as mock;
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

  Future<List<RoutePlace>> optimizeRoute(
    List<String> places,
    TravelPreference preference,
  );
}

class MockPlanRepository implements PlanRepository {
  const MockPlanRepository();

  @override
  List<String> get defaultSelectedPlaces =>
      const ['메이지 신궁', '하라주쿠', '오모테산도', '시부야'];

  @override
  Future<List<RoutePlace>> optimizeRoute(
    List<String> places,
    TravelPreference preference,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 700));
    return mock.routePlaces;
  }
}
