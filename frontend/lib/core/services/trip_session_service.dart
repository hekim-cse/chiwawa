import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_exception.dart';

final tripIdStoreProvider = Provider<TripIdStore>((ref) => TripIdStore());

final tripSessionServiceProvider = Provider<TripSessionService>((ref) {
  return TripSessionService(ref.watch(tripIdStoreProvider));
});

class TripIdStore {
  String? _tripId;

  String? get tripId => _tripId;

  Future<void> save(String tripId) async {
    _tripId = tripId;
  }

  Future<void> clear() async {
    _tripId = null;
  }
}

class TripSessionService {
  const TripSessionService(this._store);

  final TripIdStore _store;

  Future<T> loadWithRecovery<T>({
    required Future<T> Function(String tripId) loadTrip,
    required Future<String> Function() createTrip,
  }) async {
    final storedTripId = _store.tripId;

    if (storedTripId == null || storedTripId.isEmpty) {
      final createdTripId = await createTrip();
      await _store.save(createdTripId);
      return loadTrip(createdTripId);
    }

    try {
      return await loadTrip(storedTripId);
    } on ApiException catch (error) {
      if (!error.isNotFound) {
        rethrow;
      }

      await _store.clear();
      final createdTripId = await createTrip();
      await _store.save(createdTripId);
      return loadTrip(createdTripId);
    }
  }
}
