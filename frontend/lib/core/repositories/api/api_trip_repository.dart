import 'package:dio/dio.dart';

import '../../api/api_exception.dart';
import '../../models/travel_models.dart';
import '../../services/trip_session_service.dart';
import '../trip_repository.dart';

/// chiwawa_backend 실서버 구현체.
/// 백엔드 엔드포인트가 추가·변경되면 이 파일만 수정한다 (화면·Mock 영향 없음).
/// 경로 기준: backend/src/chiwawa_backend/routers/
class ApiTripRepository implements TripRepository {
  const ApiTripRepository({required this.dio, required this.tripIdStore});

  final Dio dio;
  final TripIdStore tripIdStore;

  Future<String> _requireTripId() async {
    await tripIdStore.restoreCompleted;
    final id = tripIdStore.tripId;
    if (id != null && id.isNotEmpty) return id;

    final trips = await fetchTrips();
    if (trips.isEmpty) {
      throw const ApiException('여행 정보가 없어요. 여행을 먼저 만들어 주세요.');
    }
    final fallbackId = trips.first.id;
    await tripIdStore.save(fallbackId);
    return fallbackId;
  }

  @override
  Future<List<Trip>> fetchTrips() async {
    final json = await _getJson('/api/v1/trips');
    final items = json['items'] as List<Object?>? ?? const [];
    return [
      for (final item in items)
        Trip.fromJson(Map<String, Object?>.from(item! as Map)),
    ];
  }

  @override
  Future<Trip> fetchTrip(String tripId) async {
    final json = await _getJson('/api/v1/trips/$tripId');
    return Trip.fromJson(json);
  }

  @override
  Future<Trip> createTrip(TripDraft draft) async {
    final json = await _postJson('/api/v1/trips', draft.toJson());
    return Trip.fromJson(json);
  }

  @override
  Future<Trip> updateTrip(String tripId, TripDraft draft) async {
    final json = await _patchJson(
      '/api/v1/trips/$tripId',
      draft.toJson(),
    );
    return Trip.fromJson(json);
  }

  @override
  Future<void> deleteTrip(String tripId) async {
    try {
      await dio.delete<void>('/api/v1/trips/$tripId');
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  @override
  Future<TripInfo> fetchCurrentTrip() async {
    final tripId = await _requireTripId();
    // TODO(C3): currentDay는 start_date와 오늘 날짜로 계산 — 시간대(KST/JST) 정의 필요
    // TODO(A1): weather는 백엔드 미제공 — 별도 소스 협의 전까지 빈 값
    try {
      return (await fetchTrip(tripId)).toTripInfo();
    } on ApiException catch (error) {
      if (!error.isNotFound) rethrow;

      await tripIdStore.clear();
      final recoveredId = await _requireTripId();
      return (await fetchTrip(recoveredId)).toTripInfo();
    }
  }

  @override
  Future<List<ScheduleItem>> fetchTodaySchedules() async {
    final tripId = await _requireTripId();
    final json = await _getJson('/api/v1/trips/$tripId/schedule');
    final items = json['items'] as List<Object?>? ?? const [];
    final schedules = [
      for (final item in items)
        ScheduleItem.fromJson(item! as Map<String, Object?>),
    ];
    if (schedules.isEmpty) return const [];

    final today = DateTime.now();
    final todayDate = DateTime(today.year, today.month, today.day);
    final dates = schedules
        .map((item) => DateTime.tryParse(item.date))
        .whereType<DateTime>()
        .map((date) => DateTime(date.year, date.month, date.day))
        .toSet()
        .toList()
      ..sort();
    if (dates.isEmpty) return schedules;
    final visibleDate = dates.contains(todayDate)
        ? todayDate
        : dates.firstWhere(
            (date) => date.isAfter(todayDate),
            orElse: () => dates.last,
          );
    final visibleDateText = '${visibleDate.year.toString().padLeft(4, '0')}-'
        '${visibleDate.month.toString().padLeft(2, '0')}-'
        '${visibleDate.day.toString().padLeft(2, '0')}';
    return schedules
        .where((item) => item.date == visibleDateText)
        .toList(growable: false);
  }

  @override
  Future<List<FreeTimeRecommend>> fetchFreeTimeRecommendations() async {
    final tripId = await _requireTripId();
    final json = await _getJson(
      '/api/v1/trips/$tripId/travel/free-time-recommendations',
    );
    final items = json['items'] as List<Object?>? ?? const [];
    return [
      for (final raw in items) _freeTimeFromJson(raw! as Map<String, Object?>),
    ];
  }

  FreeTimeRecommend _freeTimeFromJson(Map<String, Object?> json) {
    final minutes = (json['duration_minutes'] as num?)?.toInt();
    return FreeTimeRecommend(
      name: json['place_name'] as String? ?? json['title'] as String? ?? '',
      walk: '${(json['travel_minutes'] as num?)?.toInt() ?? 0}분',
      duration: minutes == null ? '' : '$minutes분',
    );
  }

  Future<Map<String, Object?>> _getJson(String path) async {
    try {
      final response = await dio.get<Map<String, Object?>>(path);
      return response.data ?? const {};
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  Future<Map<String, Object?>> _postJson(
    String path,
    Map<String, Object?> body,
  ) async {
    try {
      final response = await dio.post<Map<String, Object?>>(path, data: body);
      return response.data ?? const {};
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  Future<Map<String, Object?>> _patchJson(
    String path,
    Map<String, Object?> body,
  ) async {
    try {
      final response = await dio.patch<Map<String, Object?>>(path, data: body);
      return response.data ?? const {};
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }
}
