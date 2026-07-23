import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/models/photo_upload.dart';
import '../../core/models/travel_models.dart';
import '../../core/repositories/photo_place_repository.dart';

final exploreImagePathProvider = StateProvider<String?>((ref) {
  ref.watch(authSessionRevisionProvider);
  return null;
});

final explorePhotoUploadProvider = StateProvider<PhotoUpload?>((ref) {
  ref.watch(authSessionRevisionProvider);
  return null;
});

final exploreAnalyzingProvider = StateProvider<bool>((ref) {
  ref.watch(authSessionRevisionProvider);
  return false;
});

final exploreSavingPlaceProvider = StateProvider<bool>((ref) {
  ref.watch(authSessionRevisionProvider);
  return false;
});

final exploreResultVisibleProvider = StateProvider<bool>((ref) {
  ref.watch(authSessionRevisionProvider);
  return false;
});

final exploreAnalysisErrorProvider = StateProvider<String?>((ref) {
  ref.watch(authSessionRevisionProvider);
  return null;
});

final exploreSelectedResultProvider = StateProvider<PhotoSearchResult>(
  (ref) => ref.watch(photoPlaceRepositoryProvider).defaultResult,
);

final exploreCandidatesProvider = StateProvider<List<PhotoSearchResult>>(
  (ref) => [ref.watch(photoPlaceRepositoryProvider).defaultResult],
);

final exploreControllerProvider = Provider<ExploreController>((ref) {
  ref.watch(authSessionRevisionProvider);
  final controller = ExploreController(ref);
  ref.onDispose(controller.dispose);
  return controller;
});

class ExploreController {
  ExploreController(this._ref);

  final Ref _ref;
  int _analysisVersion = 0;

  void selectCandidate(PhotoSearchResult candidate) {
    _ref.read(exploreSelectedResultProvider.notifier).state = candidate;
  }

  void replaceSelectedCandidate(PhotoSearchResult updated) {
    final selected = _ref.read(exploreSelectedResultProvider);
    final candidates = _ref.read(exploreCandidatesProvider);
    _ref.read(exploreCandidatesProvider.notifier).state = List.unmodifiable([
      for (final candidate in candidates)
        if (candidate.hasSameIdentityAs(selected)) updated else candidate,
    ]);
    _ref.read(exploreSelectedResultProvider.notifier).state = updated;
  }

  void showRecentResult(PhotoSearchResult result) {
    _analysisVersion += 1;
    _ref.read(exploreSelectedResultProvider.notifier).state = result;
    _ref.read(exploreCandidatesProvider.notifier).state = [result];
    _ref.read(exploreImagePathProvider.notifier).state = null;
    _ref.read(explorePhotoUploadProvider.notifier).state = null;
    _ref.read(exploreAnalyzingProvider.notifier).state = false;
    _ref.read(exploreResultVisibleProvider.notifier).state = true;
    _ref.read(exploreAnalysisErrorProvider.notifier).state = null;
  }

  Future<bool> analyzePhoto(PhotoUpload upload) async {
    final requestVersion = ++_analysisVersion;
    _ref.read(exploreImagePathProvider.notifier).state = upload.previewPath;
    _ref.read(explorePhotoUploadProvider.notifier).state = upload;
    _ref.read(exploreAnalyzingProvider.notifier).state = true;
    _ref.read(exploreResultVisibleProvider.notifier).state = false;
    _ref.read(exploreAnalysisErrorProvider.notifier).state = null;

    try {
      final candidates = await _ref
          .read(photoPlaceRepositoryProvider)
          .analyzePhotoCandidates(upload);
      if (requestVersion != _analysisVersion) return false;

      final uniqueCandidates = _deduplicateCandidates(candidates);
      if (uniqueCandidates.isEmpty) {
        _ref.read(exploreAnalysisErrorProvider.notifier).state =
            '사진에서 장소 후보를 찾지 못했어요.';
        return false;
      }
      _ref.read(exploreCandidatesProvider.notifier).state = uniqueCandidates;
      _ref.read(exploreSelectedResultProvider.notifier).state =
          uniqueCandidates.first;
      _ref.read(exploreResultVisibleProvider.notifier).state = true;
      return true;
    } catch (_) {
      if (requestVersion == _analysisVersion) {
        _ref.read(exploreResultVisibleProvider.notifier).state = false;
        _ref.read(exploreAnalysisErrorProvider.notifier).state =
            '사진 분석을 완료하지 못했어요.';
      }
      return false;
    } finally {
      if (requestVersion == _analysisVersion) {
        _ref.read(exploreAnalyzingProvider.notifier).state = false;
      }
    }
  }

  Future<PhotoSearchResult?> confirmPhotoPlace(
    PhotoSearchResult candidate,
  ) async {
    if (_ref.read(exploreSavingPlaceProvider)) return null;
    _ref.read(exploreSavingPlaceProvider.notifier).state = true;
    try {
      final confirmed = await _ref
          .read(photoPlaceRepositoryProvider)
          .confirmPhotoPlace(candidate);
      replaceSelectedCandidate(confirmed);
      return confirmed;
    } catch (_) {
      return null;
    } finally {
      _ref.read(exploreSavingPlaceProvider.notifier).state = false;
    }
  }

  void dispose() {
    _analysisVersion += 1;
  }
}

List<PhotoSearchResult> _deduplicateCandidates(
  List<PhotoSearchResult> candidates,
) {
  final identities = <String>{};
  return List.unmodifiable(
    candidates.where((candidate) => identities.add(candidate.identityKey)),
  );
}
