import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth/auth_controller.dart';
import 'models/travel_models.dart';
import 'services/trip_session_service.dart';

final savedPhotoPlaceStoreProvider = Provider<SavedPhotoPlaceStore>(
  (ref) {
    ref.watch(authSessionRevisionProvider);
    return SavedPhotoPlaceStore();
  },
);

final savedPhotoPlacesProvider =
    StateNotifierProvider<SavedPhotoPlacesNotifier, List<PhotoSearchResult>>(
  (ref) {
    ref.watch(authSessionRevisionProvider);
    ref.watch(currentTripRevisionProvider);
    final tripId = ref.read(tripIdStoreProvider).tripId ?? 'unassigned-trip';
    return SavedPhotoPlacesNotifier(
      store: ref.watch(savedPhotoPlaceStoreProvider),
      tripId: tripId,
    );
  },
);

class SavedPhotoPlaceStore {
  final Map<String, List<PhotoSearchResult>> _placesByTrip = {};

  List<PhotoSearchResult> read(String tripId) =>
      List.unmodifiable(_placesByTrip[tripId] ?? const []);

  void write(String tripId, List<PhotoSearchResult> places) {
    _placesByTrip[tripId] = List.unmodifiable(places);
  }
}

class SavedPhotoPlacesNotifier extends StateNotifier<List<PhotoSearchResult>> {
  SavedPhotoPlacesNotifier({
    SavedPhotoPlaceStore? store,
    String tripId = 'unassigned-trip',
  }) : this._(store ?? SavedPhotoPlaceStore(), tripId);

  SavedPhotoPlacesNotifier._(this._store, this.tripId)
      : super(_store.read(tripId));

  final SavedPhotoPlaceStore _store;
  final String tripId;

  bool addPlace(PhotoSearchResult place) {
    if (state.any((item) => item.hasSameIdentityAs(place))) {
      return false;
    }

    state = List.unmodifiable([...state, place]);
    _store.write(tripId, state);
    return true;
  }

  void removePlace(PhotoSearchResult place) {
    state = state
        .where((item) => !item.hasSameIdentityAs(place))
        .toList(growable: false);
    _store.write(tripId, state);
  }

  bool containsPlace(PhotoSearchResult place) {
    return state.any((item) => item.hasSameIdentityAs(place));
  }
}
