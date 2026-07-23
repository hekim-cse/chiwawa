import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/dio_client.dart';
import '../auth/auth_controller.dart';
import '../env.dart';
import '../mock_data.dart' as mock;
import '../models/photo_upload.dart';
import '../models/travel_models.dart';
import '../services/trip_session_service.dart';
import 'api/api_photo_place_repository.dart';

final photoPlaceRepositoryProvider = Provider<PhotoPlaceRepository>((ref) {
  ref.watch(authSessionRevisionProvider);
  if (useApiBackend) {
    return ApiPhotoPlaceRepository(
      dio: ref.watch(dioClientProvider),
      tripIdStore: ref.watch(tripIdStoreProvider),
    );
  }
  return const MockPhotoPlaceRepository();
});

abstract class PhotoPlaceRepository {
  /// 화면 초기 표시용 시드(서버 데이터 아님) — Api 구현체도 동일 상수를 반환한다.
  PhotoSearchResult get defaultResult;

  Future<List<PhotoSearchResult>> fetchRecentSearches();
  Future<PhotoSearchResult> analyzePhoto(PhotoUpload upload);
  Future<List<PhotoSearchResult>> analyzePhotoCandidates(PhotoUpload upload);
  Future<PhotoSearchResult> confirmPhotoPlace(PhotoSearchResult candidate);
}

class MockPhotoPlaceRepository implements PhotoPlaceRepository {
  const MockPhotoPlaceRepository();

  @override
  PhotoSearchResult get defaultResult => mock.photoSearchResult;

  @override
  Future<List<PhotoSearchResult>> fetchRecentSearches() =>
      Future.value(mock.recentSearches);

  @override
  Future<PhotoSearchResult> analyzePhoto(PhotoUpload upload) async {
    final candidates = await analyzePhotoCandidates(upload);
    return candidates.first;
  }

  @override
  Future<List<PhotoSearchResult>> analyzePhotoCandidates(
    PhotoUpload upload,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 850));
    return [
      for (final candidate in mock.photoSearchCandidates)
        candidate.copyWith(
          searchId: 'mock-photo-search',
          imagePath: upload.previewPath,
        ),
    ];
  }

  @override
  Future<PhotoSearchResult> confirmPhotoPlace(
    PhotoSearchResult candidate,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 180));
    return candidate.copyWith(
      wantedPlaceId: candidate.wantedPlaceId.isNotEmpty
          ? candidate.wantedPlaceId
          : 'mock-wanted-${candidate.identityKey}',
    );
  }
}
