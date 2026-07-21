import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_exception.dart';

final tripIdStoreProvider = Provider<TripIdStore>((ref) {
  final store = TripIdStore();
  unawaited(store.restore());
  return store;
});

/// 선택 여행이 바뀌면 trip_id 기반 화면 데이터가 같은 프레임에서 다시 로드된다.
final currentTripRevisionProvider = StateProvider<int>((ref) => 0);

final tripSessionServiceProvider = Provider<TripSessionService>((ref) {
  return TripSessionService(ref.watch(tripIdStoreProvider));
});

class TripIdStore {
  static const _storageKey = 'current_trip_id';

  String? _tripId;
  Future<void>? _restoreTask;
  Future<void> _persistTail = Future<void>.value();
  int _mutationVersion = 0;

  String? get tripId => _tripId;

  Future<void> restore() {
    return _restoreTask ??= _restore();
  }

  Future<void> get restoreCompleted => _restoreTask ?? restore();

  Future<void> _restore() async {
    final restoreVersion = _mutationVersion;
    try {
      final prefs = await SharedPreferences.getInstance();
      if (restoreVersion != _mutationVersion) return;
      _tripId = prefs.getString(_storageKey);
    } catch (_) {
      // 저장소를 사용할 수 없는 환경에서는 현재 실행 중 값만 유지한다.
    }
  }

  Future<void> save(String tripId) {
    _mutationVersion += 1;
    _tripId = tripId;
    final operation = _persistTail.then((_) => _writeTripId(tripId));
    _persistTail = operation;
    return operation;
  }

  Future<void> _writeTripId(String tripId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_storageKey, tripId);
    } catch (_) {
      // 영속 저장 실패가 현재 여행 전환을 막지는 않는다.
    }
  }

  Future<void> clear() {
    _mutationVersion += 1;
    _tripId = null;
    final operation = _persistTail.then((_) => _removeTripId());
    _persistTail = operation;
    return operation;
  }

  Future<void> _removeTripId() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_storageKey);
    } catch (_) {
      // 영속 저장 실패가 현재 실행 중 상태를 막지는 않는다.
    }
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
