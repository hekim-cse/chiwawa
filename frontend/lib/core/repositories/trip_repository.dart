import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/dio_client.dart';
import '../env.dart';
import '../mock_data.dart' as mock;
import '../models/memorial_map_models.dart';
import '../models/travel_models.dart';
import '../services/trip_session_service.dart';
import 'api/api_trip_repository.dart';

final tripRepositoryProvider = Provider<TripRepository>((ref) {
  if (useApiBackend) {
    return ApiTripRepository(
      dio: ref.watch(dioClientProvider),
      tripIdStore: ref.watch(tripIdStoreProvider),
    );
  }
  return const MockTripRepository();
});

/// 서버 데이터 접근 계약. 실제 API는 전부 비동기이므로 Future로 통일한다.
/// Mock/Api 구현체 교체 시 화면 코드는 수정하지 않는 것이 원칙.
abstract class TripRepository {
  Future<TripInfo> fetchCurrentTrip();
  Future<List<ScheduleItem>> fetchTodaySchedules();
  Future<List<FreeTimeRecommend>> fetchFreeTimeRecommendations();
  Future<MemorialSummary> fetchMemorialSummary();
  Future<List<MemorialDay>> fetchMemorialDays();
  Future<List<DateTime>> fetchMemorialDates();
  Future<List<MemorialPhotoPoint>> fetchMemorialPhotoPoints(DateTime date);
}

class MockTripRepository implements TripRepository {
  const MockTripRepository();

  @override
  Future<TripInfo> fetchCurrentTrip() => Future.value(mock.tripInfo);

  @override
  Future<List<ScheduleItem>> fetchTodaySchedules() =>
      Future.value(mock.schedules);

  @override
  Future<List<FreeTimeRecommend>> fetchFreeTimeRecommendations() =>
      Future.value(mock.freeTimeRecommends);

  @override
  Future<MemorialSummary> fetchMemorialSummary() =>
      Future.value(mock.memorialSummary);

  @override
  Future<List<MemorialDay>> fetchMemorialDays() =>
      Future.value(mock.memorialDays);

  @override
  Future<List<DateTime>> fetchMemorialDates() =>
      Future.value(mock.memorialTripDates);

  @override
  Future<List<MemorialPhotoPoint>> fetchMemorialPhotoPoints(DateTime date) {
    final points = mock.memorialPhotoPoints.where((point) {
      return point.takenAt.year == date.year &&
          point.takenAt.month == date.month &&
          point.takenAt.day == date.day;
    }).toList();
    return Future.value(points);
  }
}
