import '../../models/place_search_models.dart';
import '../place_search_repository.dart';

/// 일반 장소 검색 API의 Swagger 계약이 확정되기 전까지 API 모드에서
/// 임의의 Google Place ID나 좌표를 만들지 않는다.
class ApiPlaceSearchRepository implements PlaceSearchRepository {
  const ApiPlaceSearchRepository();

  @override
  Future<List<PlaceSearchCandidate>> searchPlaces(
    String query, {
    String? cityBias,
  }) {
    throw const PlaceSearchException(
      '일반 장소 검색 API가 아직 준비되지 않았어요.',
    );
  }
}
