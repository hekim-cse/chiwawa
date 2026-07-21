import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/dio_client.dart';
import '../auth/auth_controller.dart';
import '../env.dart';
import '../mock_data.dart' as mock;
import '../models/travel_models.dart';
import '../services/trip_session_service.dart';
import 'api/api_trip_repository.dart';

final tripRepositoryProvider = Provider<TripRepository>((ref) {
  ref.watch(authSessionRevisionProvider);
  if (useApiBackend) {
    return ApiTripRepository(
      dio: ref.watch(dioClientProvider),
      tripIdStore: ref.watch(tripIdStoreProvider),
    );
  }
  return MockTripRepository(
    tripIdStore: ref.watch(tripIdStoreProvider),
  );
});

/// 서버 데이터 접근 계약. 실제 API는 전부 비동기이므로 Future로 통일한다.
/// Mock/Api 구현체 교체 시 화면 코드는 수정하지 않는 것이 원칙.
abstract class TripRepository {
  Future<List<Trip>> fetchTrips();
  Future<Trip> fetchTrip(String tripId);
  Future<Trip> createTrip(TripDraft draft);
  Future<Trip> updateTrip(String tripId, TripDraft draft);
  Future<void> deleteTrip(String tripId);
  Future<TripInfo> fetchCurrentTrip();
  Future<List<ScheduleItem>> fetchTodaySchedules();
  Future<List<FreeTimeRecommend>> fetchFreeTimeRecommendations();
}

class MockTripRepository implements TripRepository {
  MockTripRepository({required this.tripIdStore})
      : _trips = List<Trip>.of(mock.trips);

  final TripIdStore tripIdStore;
  final List<Trip> _trips;

  @override
  Future<List<Trip>> fetchTrips() async => List.unmodifiable(_trips);

  @override
  Future<Trip> fetchTrip(String tripId) async {
    return _trips.firstWhere((trip) => trip.id == tripId);
  }

  @override
  Future<Trip> createTrip(TripDraft draft) async {
    final trip = Trip(
      id: 'trip-mock-${DateTime.now().microsecondsSinceEpoch}',
      title: draft.title?.trim().isNotEmpty == true
          ? draft.title!.trim()
          : '${draft.city} 여행',
      city: draft.city,
      country: draft.country,
      startDate: draft.startDate,
      endDate: draft.endDate,
      travelers: draft.travelers,
      interests: List.unmodifiable(draft.interests),
      travelStyle: draft.travelStyle,
    );
    _trips.insert(0, trip);
    return trip;
  }

  @override
  Future<Trip> updateTrip(String tripId, TripDraft draft) async {
    final index = _trips.indexWhere((trip) => trip.id == tripId);
    if (index == -1) throw StateError('Trip not found');
    final current = _trips[index];
    final updated = Trip(
      id: current.id,
      title: draft.title?.trim().isNotEmpty == true
          ? draft.title!.trim()
          : current.title,
      city: draft.city,
      country: draft.country,
      startDate: draft.startDate,
      endDate: draft.endDate,
      travelers: draft.travelers,
      interests: List.unmodifiable(draft.interests),
      travelStyle: draft.travelStyle,
    );
    _trips[index] = updated;
    return updated;
  }

  @override
  Future<void> deleteTrip(String tripId) async {
    _trips.removeWhere((trip) => trip.id == tripId);
    if (tripIdStore.tripId == tripId) await tripIdStore.clear();
  }

  @override
  Future<TripInfo> fetchCurrentTrip() async {
    await tripIdStore.restoreCompleted;
    final selectedId = tripIdStore.tripId;
    Trip? trip;
    for (final item in _trips) {
      if (item.id == selectedId) {
        trip = item;
        break;
      }
    }
    if (trip == null && _trips.isNotEmpty) trip = _trips.first;
    if (trip == null) throw StateError('Trip not found');
    if (selectedId == null) await tripIdStore.save(trip.id);
    if (trip.id == mock.tripInfo.tripId) return mock.tripInfo;
    return trip.toTripInfo();
  }

  @override
  Future<List<ScheduleItem>> fetchTodaySchedules() async {
    await tripIdStore.restoreCompleted;
    final selectedId = tripIdStore.tripId ?? mock.tripInfo.tripId;
    if (selectedId != mock.tripInfo.tripId) return const [];
    return mock.schedules;
  }

  @override
  Future<List<FreeTimeRecommend>> fetchFreeTimeRecommendations() async {
    await tripIdStore.restoreCompleted;
    final selectedId = tripIdStore.tripId ?? mock.tripInfo.tripId;
    if (selectedId != mock.tripInfo.tripId) return const [];
    return mock.freeTimeRecommends;
  }
}
