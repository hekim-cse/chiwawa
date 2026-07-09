import 'package:dio/dio.dart';

import '../../mock_data.dart' as mock;
import '../../models/travel_models.dart';
import '../../services/trip_session_service.dart';
import '../photo_place_repository.dart';

/// chiwawa_backend 사진 장소 탐색 구현체.
/// POST /api/v1/trips/{trip_id}/photo-places/search
class ApiPhotoPlaceRepository implements PhotoPlaceRepository {
  const ApiPhotoPlaceRepository({required this.dio, required this.tripIdStore});

  final Dio dio;
  final TripIdStore tripIdStore;

  @override
  PhotoSearchResult get defaultResult => mock.photoSearchResult;

  @override
  Future<List<PhotoSearchResult>> fetchRecentSearches() async {
    // TODO(A5): 백엔드에 탐색 이력 조회 API가 없음 — 협의 필요. 확정 전까지 빈 목록
    return const [];
  }

  @override
  Future<PhotoSearchResult> analyzePhoto(String imagePath) async {
    // 현재 백엔드 PhotoPlaceSearchRequest는 image_url(문자열)만 받고
    // 파일 업로드 엔드포인트가 없어 로컬 사진을 전송할 방법이 없음.
    throw UnimplementedError(
      'TODO(A5): 사진 업로드 방식(multipart vs 스토리지 선업로드) 확정 후 구현',
    );
  }
}
