import 'package:dio/dio.dart';

import '../../api/api_exception.dart';
import '../../mock_data.dart' as mock;
import '../../models/photo_upload.dart';
import '../../models/travel_models.dart';
import '../../services/trip_session_service.dart';
import '../photo_place_repository.dart';

/// chiwawa_backend 사진 장소 탐색 구현체.
/// POST /api/v1/trips/{trip_id}/photo-places/search  (🔒 Bearer 필요)
class ApiPhotoPlaceRepository implements PhotoPlaceRepository {
  const ApiPhotoPlaceRepository({required this.dio, required this.tripIdStore});

  final Dio dio;
  final TripIdStore tripIdStore;

  @override
  PhotoSearchResult get defaultResult => mock.photoSearchResult;

  @override
  Future<List<PhotoSearchResult>> fetchRecentSearches() async {
    // NOTE(A5-협의): 백엔드에 탐색 이력 조회 API가 없어 확정 전까지 빈 목록.
    return const [];
  }

  @override
  Future<PhotoSearchResult> analyzePhoto(PhotoUpload upload) async {
    final candidates = await analyzePhotoCandidates(upload);
    if (candidates.isEmpty) {
      throw const ApiException('사진에서 장소 후보를 찾지 못했어요.');
    }
    return candidates.first;
  }

  @override
  Future<List<PhotoSearchResult>> analyzePhotoCandidates(
    PhotoUpload upload,
  ) async {
    final tripId = await _requireTripId();
    if (upload.isEmpty) {
      throw const ApiException('선택한 사진 파일이 비어 있어요.');
    }
    try {
      final response = await dio.post<Map<String, Object?>>(
        '/api/v1/trips/$tripId/photo-places/search',
        data: FormData.fromMap({
          'file': MultipartFile.fromBytes(
            upload.bytes,
            filename: upload.fileName,
            contentType: DioMediaType.parse(upload.mimeType),
          ),
        }),
      );
      final json = response.data ?? const {};
      final searchId = json['id']?.toString() ?? '';
      final candidates = json['candidates'] as List<Object?>? ?? const [];
      return [
        for (final raw in candidates)
          _candidateToResult(
            Map<String, Object?>.from(raw! as Map),
            searchId: searchId,
            imagePath: upload.previewPath,
          ),
      ];
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  @override
  Future<PhotoSearchResult> confirmPhotoPlace(
    PhotoSearchResult candidate,
  ) async {
    if (candidate.wantedPlaceId.isNotEmpty) return candidate;
    if (candidate.searchId.isEmpty || candidate.id.isEmpty) {
      throw const ApiException('장소 후보 식별 정보가 없어요. 사진을 다시 분석해 주세요.');
    }
    final tripId = await _requireTripId();
    try {
      final response = await dio.post<Map<String, Object?>>(
        '/api/v1/trips/$tripId/photo-places/${candidate.searchId}/confirm',
        data: {'candidate_id': candidate.id},
      );
      final json = response.data ?? const {};
      final wantedPlace = Map<String, Object?>.from(
        json['wanted_place'] as Map? ?? const {},
      );
      return candidate.copyWith(
        wantedPlaceId: wantedPlace['id']?.toString() ?? '',
      );
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  PhotoSearchResult _candidateToResult(
    Map<String, Object?> json, {
    required String searchId,
    required String imagePath,
  }) {
    final city = json['city'] as String? ?? '';
    final country = json['country'] as String? ?? '';
    final address = [city, country].where((part) => part.isNotEmpty).join(', ');
    return PhotoSearchResult(
      id: json['id'] as String? ?? '',
      searchId: searchId,
      name: json['name'] as String? ?? '',
      address: address,
      category: '',
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      confidence: (json['confidence'] as num?)?.toDouble(),
      imagePath: imagePath,
    );
  }

  Future<String> _requireTripId() async {
    await tripIdStore.restoreCompleted;
    final id = tripIdStore.tripId;
    if (id == null || id.isEmpty) {
      throw const ApiException('여행 정보가 없어요. 여행을 먼저 만들어 주세요.');
    }
    return id;
  }
}
