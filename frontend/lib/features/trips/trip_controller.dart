import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/models/travel_models.dart';
import '../../core/repositories/trip_repository.dart';
import '../../core/services/trip_session_service.dart';

enum TripCatalogStatus { initial, loading, ready, error }

class TripCatalogState {
  const TripCatalogState({
    this.status = TripCatalogStatus.initial,
    this.trips = const [],
    this.currentTripId,
    this.errorMessage,
    this.isCreating = false,
  });

  final TripCatalogStatus status;
  final List<Trip> trips;
  final String? currentTripId;
  final String? errorMessage;
  final bool isCreating;

  Trip? get currentTrip {
    for (final trip in trips) {
      if (trip.id == currentTripId) return trip;
    }
    return null;
  }

  TripCatalogState copyWith({
    TripCatalogStatus? status,
    List<Trip>? trips,
    String? currentTripId,
    String? errorMessage,
    bool clearCurrentTrip = false,
    bool clearError = false,
    bool? isCreating,
  }) {
    return TripCatalogState(
      status: status ?? this.status,
      trips: trips ?? this.trips,
      currentTripId:
          clearCurrentTrip ? null : currentTripId ?? this.currentTripId,
      errorMessage: clearError ? null : errorMessage ?? this.errorMessage,
      isCreating: isCreating ?? this.isCreating,
    );
  }
}

final tripCatalogProvider =
    StateNotifierProvider<TripCatalogController, TripCatalogState>((ref) {
  ref.watch(authSessionRevisionProvider);
  final controller = TripCatalogController(ref);
  unawaited(controller.load());
  return controller;
});

class TripCatalogController extends StateNotifier<TripCatalogState> {
  TripCatalogController(this._ref) : super(const TripCatalogState());

  final Ref _ref;

  TripRepository get _repository => _ref.read(tripRepositoryProvider);
  TripIdStore get _store => _ref.read(tripIdStoreProvider);

  Future<void> load() async {
    state = state.copyWith(
      status: TripCatalogStatus.loading,
      clearError: true,
    );
    try {
      await _store.restoreCompleted;
      final trips = await _repository.fetchTrips();
      final storedId = _store.tripId;
      final hasStoredTrip = trips.any((trip) => trip.id == storedId);
      final selectedId = hasStoredTrip
          ? storedId
          : trips.isEmpty
              ? null
              : trips.first.id;

      if (selectedId == null) {
        await _store.clear();
      } else {
        await _store.save(selectedId);
      }

      state = TripCatalogState(
        status: TripCatalogStatus.ready,
        trips: List.unmodifiable(trips),
        currentTripId: selectedId,
      );
      _refreshTripData();
    } catch (error) {
      state = TripCatalogState(
        status: TripCatalogStatus.error,
        trips: state.trips,
        currentTripId: state.currentTripId,
        errorMessage: mapApiErrorToMessage(error),
      );
    }
  }

  Future<Trip?> createTrip(TripDraft draft) async {
    state = state.copyWith(isCreating: true, clearError: true);
    try {
      final trip = await _repository.createTrip(draft);
      await _store.save(trip.id);
      state = state.copyWith(
        status: TripCatalogStatus.ready,
        trips: List.unmodifiable([trip, ...state.trips]),
        currentTripId: trip.id,
        isCreating: false,
        clearError: true,
      );
      _refreshTripData();
      return trip;
    } catch (error) {
      state = state.copyWith(
        isCreating: false,
        errorMessage: mapApiErrorToMessage(error),
      );
      return null;
    }
  }

  Future<void> selectTrip(String tripId) async {
    if (tripId == state.currentTripId ||
        !state.trips.any((trip) => trip.id == tripId)) {
      return;
    }
    await _store.save(tripId);
    state = state.copyWith(currentTripId: tripId, clearError: true);
    _refreshTripData();
  }

  Future<Trip?> updateTrip(String tripId, TripDraft draft) async {
    try {
      final updated = await _repository.updateTrip(tripId, draft);
      state = state.copyWith(
        trips: List.unmodifiable([
          for (final trip in state.trips)
            if (trip.id == tripId) updated else trip,
        ]),
        clearError: true,
      );
      if (tripId == state.currentTripId) _refreshTripData();
      return updated;
    } catch (error) {
      state = state.copyWith(errorMessage: mapApiErrorToMessage(error));
      return null;
    }
  }

  Future<void> deleteTrip(String tripId) async {
    try {
      await _repository.deleteTrip(tripId);
      final remaining = state.trips
          .where((trip) => trip.id != tripId)
          .toList(growable: false);
      var selectedId = state.currentTripId;
      if (selectedId == tripId) {
        selectedId = remaining.isEmpty ? null : remaining.first.id;
        if (selectedId == null) {
          await _store.clear();
        } else {
          await _store.save(selectedId);
        }
      }
      state = TripCatalogState(
        status: TripCatalogStatus.ready,
        trips: remaining,
        currentTripId: selectedId,
      );
      _refreshTripData();
    } catch (error) {
      state = state.copyWith(errorMessage: mapApiErrorToMessage(error));
    }
  }

  void _refreshTripData() {
    final revision = _ref.read(currentTripRevisionProvider.notifier);
    revision.state += 1;
  }
}
