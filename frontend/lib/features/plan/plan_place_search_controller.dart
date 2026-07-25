import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/models/place_search_models.dart';
import '../../core/repositories/place_search_repository.dart';
import '../../core/services/trip_session_service.dart';

enum PlanPlaceRole { start, end }

enum PlanPlaceSearchStatus { idle, loading, success, empty, failure }

class PlanPlaceSearchKey {
  const PlanPlaceSearchKey({
    required this.day,
    required this.role,
  });

  final int day;
  final PlanPlaceRole role;

  @override
  bool operator ==(Object other) {
    return other is PlanPlaceSearchKey &&
        other.day == day &&
        other.role == role;
  }

  @override
  int get hashCode => Object.hash(day, role);
}

class PlanPlaceSearchState {
  const PlanPlaceSearchState({
    this.query = '',
    this.status = PlanPlaceSearchStatus.idle,
    this.results = const [],
    this.message,
  });

  final String query;
  final PlanPlaceSearchStatus status;
  final List<PlaceSearchCandidate> results;
  final String? message;

  PlanPlaceSearchState copyWith({
    String? query,
    PlanPlaceSearchStatus? status,
    List<PlaceSearchCandidate>? results,
    String? message,
    bool clearMessage = false,
  }) {
    return PlanPlaceSearchState(
      query: query ?? this.query,
      status: status ?? this.status,
      results: results ?? this.results,
      message: clearMessage ? null : message ?? this.message,
    );
  }
}

class PlanPlaceSearchStates {
  const PlanPlaceSearchStates({this.statesByKey = const {}});

  final Map<PlanPlaceSearchKey, PlanPlaceSearchState> statesByKey;

  PlanPlaceSearchState forKey(PlanPlaceSearchKey key) {
    return statesByKey[key] ?? const PlanPlaceSearchState();
  }
}

final planPlaceSearchStoreProvider = Provider<PlanPlaceSearchStore>((ref) {
  ref.watch(authSessionRevisionProvider);
  return PlanPlaceSearchStore();
});

final planPlaceSearchProvider =
    StateNotifierProvider<PlanPlaceSearchController, PlanPlaceSearchStates>(
  (ref) {
    ref.watch(authSessionRevisionProvider);
    ref.watch(currentTripRevisionProvider);
    final tripId = ref.read(tripIdStoreProvider).tripId ?? 'unassigned-trip';
    return PlanPlaceSearchController(
      repository: ref.watch(placeSearchRepositoryProvider),
      store: ref.watch(planPlaceSearchStoreProvider),
      tripId: tripId,
    );
  },
);

class PlanPlaceSearchStore {
  final Map<String, Map<PlanPlaceSearchKey, PlanPlaceSearchState>>
      _statesByTrip = {};

  Map<PlanPlaceSearchKey, PlanPlaceSearchState> read(String tripId) {
    return Map<PlanPlaceSearchKey, PlanPlaceSearchState>.unmodifiable(
      _statesByTrip[tripId] ?? const {},
    );
  }

  void write(
    String tripId,
    Map<PlanPlaceSearchKey, PlanPlaceSearchState> states,
  ) {
    _statesByTrip[tripId] =
        Map<PlanPlaceSearchKey, PlanPlaceSearchState>.unmodifiable(states);
  }
}

class PlanPlaceSearchController extends StateNotifier<PlanPlaceSearchStates> {
  PlanPlaceSearchController({
    required PlaceSearchRepository repository,
    PlanPlaceSearchStore? store,
    String tripId = 'unassigned-trip',
    Duration debounceDuration = const Duration(milliseconds: 280),
  }) : this._(
          repository,
          store ?? PlanPlaceSearchStore(),
          tripId,
          debounceDuration,
        );

  PlanPlaceSearchController._(
    this._repository,
    this._store,
    this.tripId,
    this.debounceDuration,
  ) : super(
          PlanPlaceSearchStates(
            statesByKey: _store.read(tripId),
          ),
        );

  final PlaceSearchRepository _repository;
  final PlanPlaceSearchStore _store;
  final String tripId;
  final Duration debounceDuration;
  final Map<PlanPlaceSearchKey, Timer> _debounceTimers = {};
  final Map<PlanPlaceSearchKey, int> _requestVersions = {};
  final Map<PlanPlaceSearchKey, String?> _cityBiases = {};

  void updateQuery(
    PlanPlaceSearchKey key,
    String value, {
    String? cityBias,
  }) {
    _cityBiases[key] = cityBias;
    _debounceTimers.remove(key)?.cancel();
    final version = (_requestVersions[key] ?? 0) + 1;
    _requestVersions[key] = version;
    final query = value.trimLeft();
    if (query.trim().isEmpty) {
      _set(
        key,
        const PlanPlaceSearchState(),
      );
      return;
    }

    _set(
      key,
      PlanPlaceSearchState(
        query: query,
        status: PlanPlaceSearchStatus.loading,
      ),
    );
    _debounceTimers[key] = Timer(
      debounceDuration,
      () => unawaited(_search(key, query, version)),
    );
  }

  Future<void> searchImmediately(
    PlanPlaceSearchKey key, {
    String? cityBias,
  }) async {
    _cityBiases[key] = cityBias ?? _cityBiases[key];
    _debounceTimers.remove(key)?.cancel();
    final current = state.forKey(key);
    final query = current.query.trim();
    if (query.isEmpty) {
      _set(key, const PlanPlaceSearchState());
      return;
    }
    final version = (_requestVersions[key] ?? 0) + 1;
    _requestVersions[key] = version;
    _set(
      key,
      current.copyWith(
        status: PlanPlaceSearchStatus.loading,
        results: const [],
        clearMessage: true,
      ),
    );
    await _search(key, query, version);
  }

  Future<void> retry(PlanPlaceSearchKey key) => searchImmediately(key);

  void selectPlace(PlanPlaceSearchKey key, PlaceSearchCandidate place) {
    _debounceTimers.remove(key)?.cancel();
    _requestVersions[key] = (_requestVersions[key] ?? 0) + 1;
    _set(
      key,
      PlanPlaceSearchState(query: place.name),
    );
  }

  Future<void> _search(
    PlanPlaceSearchKey key,
    String query,
    int version,
  ) async {
    try {
      final results = await _repository.searchPlaces(
        query,
        cityBias: _cityBiases[key],
      );
      if (_requestVersions[key] != version) return;
      _set(
        key,
        PlanPlaceSearchState(
          query: query,
          status: results.isEmpty
              ? PlanPlaceSearchStatus.empty
              : PlanPlaceSearchStatus.success,
          results: List<PlaceSearchCandidate>.unmodifiable(results),
        ),
      );
    } catch (error) {
      if (_requestVersions[key] != version) return;
      final message =
          error is PlaceSearchException ? error.message : '장소를 검색하지 못했어요.';
      _set(
        key,
        PlanPlaceSearchState(
          query: query,
          status: PlanPlaceSearchStatus.failure,
          message: message,
        ),
      );
    }
  }

  void _set(PlanPlaceSearchKey key, PlanPlaceSearchState value) {
    final states = Map<PlanPlaceSearchKey, PlanPlaceSearchState>.unmodifiable({
      ...state.statesByKey,
      key: value,
    });
    state = PlanPlaceSearchStates(statesByKey: states);
    _store.write(tripId, states);
  }

  @override
  void dispose() {
    for (final timer in _debounceTimers.values) {
      timer.cancel();
    }
    super.dispose();
  }
}
