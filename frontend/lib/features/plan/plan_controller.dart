import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/models/transport_mode.dart';
import '../../core/models/travel_models.dart';
import '../../core/repositories/plan_repository.dart';
import '../../core/services/trip_session_service.dart';
import 'models/plan_itinerary.dart';
import 'models/plan_place_selection.dart';

final selectedPlacesProvider = StateProvider<List<PlanPlaceSelection>>((ref) {
  ref.watch(currentTripRevisionProvider);
  final names = ref.watch(planRepositoryProvider).defaultSelectedPlaces;
  return List.unmodifiable([
    for (var index = 0; index < names.length; index++)
      PlanPlaceSelection(
        id: 'seed:$index',
        name: names[index],
        source: PlanPlaceSource.seed,
      ),
  ]);
});

final travelPreferenceProvider = StateProvider<TravelPreference>(
  (ref) {
    ref.watch(authSessionRevisionProvider);
    ref.watch(currentTripRevisionProvider);
    return const TravelPreference();
  },
);

final transportModeProvider = StateProvider<TransportMode>((ref) {
  ref.watch(authSessionRevisionProvider);
  ref.watch(currentTripRevisionProvider);
  return TransportMode.transit;
});

final routeOptimizationProvider =
    StateNotifierProvider<RouteOptimizationController, RouteOptimizationState>(
        (ref) {
  ref.watch(authSessionRevisionProvider);
  ref.watch(currentTripRevisionProvider);
  return RouteOptimizationController(ref);
});

final planActionsProvider = Provider<PlanActions>(PlanActions.new);

final planItineraryProvider =
    StateNotifierProvider<PlanItineraryController, PlanItineraryState>((ref) {
  ref.watch(authSessionRevisionProvider);
  ref.watch(currentTripRevisionProvider);
  return PlanItineraryController();
});

class PlanItineraryController extends StateNotifier<PlanItineraryState> {
  PlanItineraryController() : super(const PlanItineraryState());

  void selectDay(int day) {
    if (day == state.selectedDay || day < 1) return;
    state = state.copyWith(selectedDay: day);
  }

  void replaceCurrentDay(List<RoutePlace> places) {
    final stops = <PlanItineraryStop>[
      for (var index = 0; index < places.length; index++)
        PlanItineraryStop(
          id: '${places[index].identityKey}-$index',
          startTime: _timeForIndex(index),
          place: places[index],
        ),
    ];
    _setCurrentStops(stops);
  }

  void clearCurrentDay() => _setCurrentStops(const <PlanItineraryStop>[]);

  void move(int fromIndex, int toIndex) {
    final stops = [...state.currentStops];
    if (fromIndex < 0 ||
        fromIndex >= stops.length ||
        toIndex < 0 ||
        toIndex >= stops.length ||
        fromIndex == toIndex) {
      return;
    }
    final stop = stops.removeAt(fromIndex);
    stops.insert(toIndex, stop);
    _setCurrentStops(stops);
  }

  void updateTime(String stopId, String startTime) {
    _setCurrentStops([
      for (final stop in state.currentStops)
        if (stop.id == stopId) stop.copyWith(startTime: startTime) else stop,
    ]);
  }

  void remove(String stopId) {
    _setCurrentStops(
      state.currentStops
          .where((stop) => stop.id != stopId)
          .toList(growable: false),
    );
  }

  void _setCurrentStops(List<PlanItineraryStop> stops) {
    state = state.copyWith(
      stopsByDay: Map<int, List<PlanItineraryStop>>.unmodifiable({
        ...state.stopsByDay,
        state.selectedDay: List<PlanItineraryStop>.unmodifiable(stops),
      }),
    );
  }
}

String _timeForIndex(int index) {
  final totalMinutes = 9 * 60 + index * 120;
  final hour = (totalMinutes ~/ 60).clamp(0, 23);
  final minute = totalMinutes % 60;
  return '${hour.toString().padLeft(2, '0')}:'
      '${minute.toString().padLeft(2, '0')}';
}

class PlanActions {
  PlanActions(this._ref);

  final Ref _ref;
  int _selectionSequence = 0;

  bool addPlace(
    String value, {
    PlanPlaceSource source = PlanPlaceSource.manual,
  }) {
    final place = value.trim();
    if (place.isEmpty) return false;
    return _addSelection(
      PlanPlaceSelection(
        id: '${source.name}:${_selectionSequence++}',
        name: place,
        source: source,
      ),
    );
  }

  bool addSavedPlace(PhotoSearchResult place) {
    return _addSelection(PlanPlaceSelection.fromPhoto(place));
  }

  bool _addSelection(PlanPlaceSelection selection) {
    final places = _ref.read(selectedPlacesProvider);
    if (places.any((place) => place.id == selection.id)) return false;
    _ref.read(selectedPlacesProvider.notifier).state =
        List.unmodifiable([...places, selection]);
    resetOptimization();
    return true;
  }

  void removePlace(PlanPlaceSelection place) {
    final places = _ref.read(selectedPlacesProvider);
    _ref.read(selectedPlacesProvider.notifier).state = List.unmodifiable(
      places.where((item) => item.id != place.id),
    );
    resetOptimization();
  }

  void updateTheme(TravelTheme theme, bool selected) {
    final preference = _ref.read(travelPreferenceProvider);
    final nextThemes = {...preference.themes};
    if (selected) {
      nextThemes.add(theme);
    } else if (nextThemes.length > 1) {
      nextThemes.remove(theme);
    }
    _ref.read(travelPreferenceProvider.notifier).state =
        preference.copyWith(themes: nextThemes);
    resetOptimization();
  }

  void updatePace(TravelPace pace) {
    final preference = _ref.read(travelPreferenceProvider);
    _ref.read(travelPreferenceProvider.notifier).state =
        preference.copyWith(pace: pace);
    resetOptimization();
  }

  void updateTransportMode(TransportMode mode) {
    final currentMode = _ref.read(transportModeProvider);
    if (currentMode == mode) return;
    final routeState = _ref.read(routeOptimizationProvider);
    final shouldReoptimize =
        routeState.status == AiJobStatus.done || routeState.isWorking;
    _ref.read(transportModeProvider.notifier).state = mode;
    resetOptimization();
    if (shouldReoptimize) {
      unawaited(optimizeRoute(mode));
    }
  }

  Future<void> optimizeRoute(TransportMode transportMode) {
    return _ref
        .read(routeOptimizationProvider.notifier)
        .optimize(transportMode);
  }

  void resetOptimization() {
    _ref.read(routeOptimizationProvider.notifier).reset();
    _ref.read(planItineraryProvider.notifier).clearCurrentDay();
  }
}

class RouteOptimizationController
    extends StateNotifier<RouteOptimizationState> {
  RouteOptimizationController(this._ref)
      : super(const RouteOptimizationState.idle());

  final Ref _ref;
  int _requestVersion = 0;

  Future<void> optimize(TransportMode transportMode) async {
    final requestVersion = ++_requestVersion;
    final selections = _ref.read(selectedPlacesProvider);
    final places = List<String>.unmodifiable(
      selections.map((selection) => selection.name),
    );
    final preference = _ref.read(travelPreferenceProvider);

    state = const RouteOptimizationState.pending();
    await Future<void>.delayed(const Duration(milliseconds: 180));
    if (requestVersion != _requestVersion) return;
    state = const RouteOptimizationState.running();

    try {
      final routePlaces = await _ref
          .read(planRepositoryProvider)
          .optimizeRoute(places, preference, transportMode);
      if (requestVersion != _requestVersion) return;
      state = RouteOptimizationState.done(List.unmodifiable(routePlaces));
      _ref.read(planItineraryProvider.notifier).replaceCurrentDay(routePlaces);
    } catch (_) {
      if (requestVersion != _requestVersion) return;
      state = const RouteOptimizationState.failed(
        '경로 최적화에 실패했어요. 다시 시도해 주세요.',
      );
    }
  }

  void reset() {
    _requestVersion += 1;
    state = const RouteOptimizationState.idle();
  }
}
