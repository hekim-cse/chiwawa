import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/models/place_search_models.dart';
import '../../core/services/trip_session_service.dart';
import 'models/plan_day_constraint.dart';

final planDayConstraintStoreProvider = Provider<PlanDayConstraintStore>((ref) {
  ref.watch(authSessionRevisionProvider);
  return PlanDayConstraintStore();
});

final planDayConstraintsProvider = StateNotifierProvider<
    PlanDayConstraintsController, PlanDayConstraintsState>((ref) {
  ref.watch(authSessionRevisionProvider);
  ref.watch(currentTripRevisionProvider);
  final tripId = ref.read(tripIdStoreProvider).tripId ?? 'unassigned-trip';
  return PlanDayConstraintsController(
    store: ref.watch(planDayConstraintStoreProvider),
    tripId: tripId,
  );
});

class PlanDayConstraintStore {
  final Map<String, Map<int, PlanDayConstraint>> _constraintsByTrip = {};

  Map<int, PlanDayConstraint> read(String tripId) {
    return Map<int, PlanDayConstraint>.unmodifiable(
      _constraintsByTrip[tripId] ?? const {},
    );
  }

  void write(String tripId, Map<int, PlanDayConstraint> constraints) {
    _constraintsByTrip[tripId] =
        Map<int, PlanDayConstraint>.unmodifiable(constraints);
  }
}

class PlanDayConstraintsController
    extends StateNotifier<PlanDayConstraintsState> {
  PlanDayConstraintsController({
    PlanDayConstraintStore? store,
    String tripId = 'unassigned-trip',
  }) : this._(store ?? PlanDayConstraintStore(), tripId);

  PlanDayConstraintsController._(this._store, this.tripId)
      : super(
          PlanDayConstraintsState(
            constraintsByDay: _store.read(tripId),
          ),
        );

  final PlanDayConstraintStore _store;
  final String tripId;

  void selectStartPlace(int day, PlaceSearchCandidate place) {
    _update(day, state.forDay(day).copyWith(startPlace: place));
  }

  void clearStartPlace(int day) {
    _update(day, state.forDay(day).copyWith(clearStartPlace: true));
  }

  void updateStartTime(int day, String value) {
    _update(day, state.forDay(day).copyWith(startTime: value));
  }

  void selectEndPlace(int day, PlaceSearchCandidate place) {
    _update(day, state.forDay(day).copyWith(endPlace: place));
  }

  void clearEndPlace(int day) {
    _update(day, state.forDay(day).copyWith(clearEndPlace: true));
  }

  void updateEndTime(int day, String value) {
    _update(day, state.forDay(day).copyWith(endTime: value));
  }

  void _update(int day, PlanDayConstraint constraint) {
    if (day < 1) return;
    final constraints = Map<int, PlanDayConstraint>.unmodifiable({
      ...state.constraintsByDay,
      day: constraint,
    });
    state = state.copyWith(constraintsByDay: constraints);
    _store.write(tripId, constraints);
  }
}
