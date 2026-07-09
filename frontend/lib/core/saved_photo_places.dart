import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'models/travel_models.dart';

final savedPhotoPlacesProvider =
    StateNotifierProvider<SavedPhotoPlacesNotifier, List<PhotoSearchResult>>(
  (ref) => SavedPhotoPlacesNotifier(),
);

class SavedPhotoPlacesNotifier extends StateNotifier<List<PhotoSearchResult>> {
  SavedPhotoPlacesNotifier() : super(const []);

  bool addPlace(PhotoSearchResult place) {
    if (state.any((item) => item.name == place.name)) {
      return false;
    }

    state = [...state, place];
    return true;
  }

  void removePlace(PhotoSearchResult place) {
    state = state.where((item) => item.name != place.name).toList();
  }

  bool containsPlace(PhotoSearchResult place) {
    return state.any((item) => item.name == place.name);
  }
}
