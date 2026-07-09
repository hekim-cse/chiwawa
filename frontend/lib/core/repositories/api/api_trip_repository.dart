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

  String get _tripId {
    final id = tripIdStore.tripId;
    if (id == null || id.isEmpty) {
      // TODO(A3): trip 생성 흐름 확정 후 TripSessionService.loadWithRecovery 연결
      throw const ApiException('여행 정보가 없어요. 여행을 먼저 만들어 주세요.');
    }
    return id;
  }

  @override
  Future<TripInfo> fetchCurrentTrip() async {
    // TODO(C3): currentDay는 start_date와 오늘 날짜로 계산 — 시간대(KST/JST) 정의 필요
    // TODO(A1): weather는 백엔드 미제공 — 별도 소스 협의 전까지 빈 값
    final json = await _getJson('/api/v1/trips/$_tripId');
    return TripInfo.fromJson(json);
  }

  @override
  Future<List<ScheduleItem>> fetchTodaySchedules() async {
    final json = await _getJson('/api/v1/trips/$_tripId/travel/today');
    final schedule = json['schedule'] as Map<String, Object?>? ?? const {};
    final items = schedule['items'] as List<Object?>? ?? const [];
    return [
      for (final item in items)
        ScheduleItem.fromJson(item! as Map<String, Object?>),
    ];
  }

  @override
  Future<List<FreeTimeRecommend>> fetchFreeTimeRecommendations() async {
    // TODO(C4): date/start_time/end_time을 실제 빈 시간대 기준으로 계산해 전달
    final json = await _postJson(
      '/api/v1/trips/$_tripId/travel/free-time-recommendations',
      const {},
    );
    final items = json['items'] as List<Object?>? ?? const [];
    return [
      for (final raw in items)
        _freeTimeFromJson(raw! as Map<String, Object?>),
    ];
  }

  FreeTimeRecommend _freeTimeFromJson(Map<String, Object?> json) {
    final minutes = (json['duration_minutes'] as num?)?.toInt();
    return FreeTimeRecommend(
      name: json['place_name'] as String? ?? json['title'] as String? ?? '',
      // TODO(A1): 백엔드 응답에 도보 거리(walk) 없음 — 협의 후 매핑
      walk: '',
      duration: minutes == null ? '' : '$minutes분',
    );
  }

  @override
  Future<MemorialSummary> fetchMemorialSummary() async {
    // GET /api/v1/trips/{tripId}/memorial
    throw UnimplementedError('TODO(C6): memorial 응답 매핑 확정 후 구현');
  }

  @override
  Future<List<MemorialDay>> fetchMemorialDays() async {
    // GET /api/v1/trips/{tripId}/memorial/photos
    throw UnimplementedError('TODO(C6): memorial 사진 매핑 확정 후 구현');
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
}
