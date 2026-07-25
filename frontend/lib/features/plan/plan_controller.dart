import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/models/route_planning_models.dart';
import '../../core/models/transport_mode.dart';
import '../../core/models/travel_models.dart';
import '../../core/repositories/plan_repository.dart';
import '../../core/services/trip_session_service.dart';
import 'models/plan_itinerary.dart';
import 'models/plan_place_selection.dart';
import 'plan_day_constraints_controller.dart';

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

  void replaceCurrentDay(
    List<RoutePlace> places, {
    String startTime = '09:00',
    RouteTimeline? timeline,
  }) {
    final timelineStops = timeline?.timelineStops
            .where((stop) => stop.stopType == 'POI')
            .toList(growable: false) ??
        const <RouteTimelineStop>[];
    final stops = <PlanItineraryStop>[
      for (var index = 0; index < places.length; index++)
        PlanItineraryStop(
          id: '${places[index].identityKey}-$index',
          startTime: index < timelineStops.length
              ? timelineStops[index].arrivalTime
              : _timeForIndex(index, startTime),
          departureTime: index < timelineStops.length
              ? timelineStops[index].departureTime
              : null,
          stayMinutes: index < timelineStops.length
              ? timelineStops[index].stayMinutes
              : null,
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

String _timeForIndex(int index, String startTime) {
  final parts = startTime.split(':');
  final startHour = int.tryParse(parts.first) ?? 9;
  final startMinute = parts.length > 1 ? int.tryParse(parts[1]) ?? 0 : 0;
  final totalMinutes = startHour * 60 + startMinute + index * 120;
  final hour = (totalMinutes ~/ 60).clamp(0, 23);
  final minute = totalMinutes % 60;
  return '${hour.toString().padLeft(2, '0')}:'
      '${minute.toString().padLeft(2, '0')}';
}

class PlanActions {
  PlanActions(this._ref);

  final Ref _ref;
  int _selectionSequence = 0;
  final Set<String> _pendingPlaceNames = {};

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

  Future<bool> saveAndAddPlace(String value) async {
    final name = value.trim();
    if (name.isEmpty || !_pendingPlaceNames.add(name)) return false;
    final localId = 'manual:${_selectionSequence++}';
    try {
      final record = await _ref.read(planRepositoryProvider).saveWantedPlace(
            PlanRoutePlaceInput(localId: localId, name: name),
          );
      return _addSelection(
        PlanPlaceSelection(
          id: localId,
          name: record.name.isEmpty ? name : record.name,
          address: record.address,
          source: PlanPlaceSource.manual,
          serverPlaceId: record.id,
          latitude: record.latitude,
          longitude: record.longitude,
        ),
      );
    } finally {
      _pendingPlaceNames.remove(name);
    }
  }

  Future<bool> addRecommendation(RouteRecommendation recommendation) async {
    final candidate = recommendation.candidate;
    final localId = 'recommendation:${candidate.placeId}';
    final existing = _ref
        .read(selectedPlacesProvider)
        .any((selection) => selection.id == localId);
    if (existing) return false;
    final record = await _ref.read(planRepositoryProvider).saveWantedPlace(
          PlanRoutePlaceInput(
            localId: localId,
            name: candidate.name,
            address: candidate.formattedAddress,
            latitude: candidate.latitude,
            longitude: candidate.longitude,
          ),
        );
    final added = _addSelection(
      PlanPlaceSelection(
        id: localId,
        name: candidate.name,
        address: candidate.formattedAddress,
        source: PlanPlaceSource.freeTime,
        serverPlaceId: record.id,
        latitude: candidate.latitude,
        longitude: candidate.longitude,
      ),
    );
    if (added) {
      await optimizeRoute(_ref.read(transportModeProvider));
    }
    return added;
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
    final selectedDay = _ref.read(planItineraryProvider).selectedDay;
    final dayConstraint =
        _ref.read(planDayConstraintsProvider).forDay(selectedDay);
    if (!dayConstraint.isValid) {
      state = const RouteOptimizationState.idle();
      return;
    }
    final preference = _ref.read(travelPreferenceProvider);

    state = const RouteOptimizationState.pending();
    await Future<void>.delayed(const Duration(milliseconds: 180));
    if (requestVersion != _requestVersion) return;
    state = const RouteOptimizationState.running();

    try {
      final selections = await _persistSelections(
        _ref.read(selectedPlacesProvider),
      );
      if (requestVersion != _requestVersion) return;
      _ref.read(selectedPlacesProvider.notifier).state =
          List.unmodifiable(selections);
      final result = await _ref.read(planRepositoryProvider).optimizeRoute(
            RouteOptimizationRequest(
              places: [
                for (final selection in selections)
                  PlanRoutePlaceInput(
                    localId: selection.id,
                    serverPlaceId: selection.serverPlaceId,
                    name: selection.name,
                    address: selection.address,
                    latitude: selection.latitude,
                    longitude: selection.longitude,
                  ),
              ],
              preference: preference,
              transportMode: transportMode,
              dayIndex: selectedDay,
              plannedStartTime: dayConstraint.startTime,
              plannedEndTime: dayConstraint.endTime,
              maxPlaceCount: dayConstraint.maxPlaceCount,
              startPlace: dayConstraint.startPlace!,
              endPlace: dayConstraint.endPlace!,
            ),
          );
      if (requestVersion != _requestVersion) return;
      final filteredResult = _excludeSelectedRecommendations(
        result,
        selections,
      );
      final limitedResult =
          _limitResult(filteredResult, dayConstraint.maxPlaceCount);
      state = RouteOptimizationState.done(limitedResult);
      if (!limitedResult.isAvailable) {
        _ref.read(planItineraryProvider.notifier).clearCurrentDay();
        return;
      }
      _ref.read(planItineraryProvider.notifier).replaceCurrentDay(
            limitedResult.places,
            startTime: dayConstraint.startTime,
            timeline: limitedResult.timeline,
          );
    } catch (_) {
      if (requestVersion != _requestVersion) return;
      state = const RouteOptimizationState.failed(
        '경로 최적화에 실패했어요. 다시 시도해 주세요.',
      );
    }
  }

  RouteOptimizationResult _excludeSelectedRecommendations(
    RouteOptimizationResult result,
    List<PlanPlaceSelection> selections,
  ) {
    final selectedIds = selections.map((selection) => selection.id).toSet();
    final groups = [
      for (final group in result.recommendationGroups)
        if (group.recommendations.any(
          (recommendation) => !selectedIds.contains(
            'recommendation:${recommendation.candidate.placeId}',
          ),
        ))
          RouteRecommendationGroup(
            category: group.category,
            displayName: group.displayName,
            recommendations: [
              for (final recommendation in group.recommendations)
                if (!selectedIds.contains(
                  'recommendation:${recommendation.candidate.placeId}',
                ))
                  recommendation,
            ],
          ),
    ];
    return RouteOptimizationResult(
      availability: result.availability,
      places: result.places,
      timeline: result.timeline,
      missingSegments: result.missingSegments,
      warnings: result.warnings,
      recommendationGroups: groups,
    );
  }

  Future<List<PlanPlaceSelection>> _persistSelections(
    List<PlanPlaceSelection> selections,
  ) async {
    final repository = _ref.read(planRepositoryProvider);
    final persisted = <PlanPlaceSelection>[];
    for (final selection in selections) {
      if (selection.isPersisted) {
        persisted.add(selection);
        continue;
      }
      final record = await repository.saveWantedPlace(
        PlanRoutePlaceInput(
          localId: selection.id,
          name: selection.name,
          address: selection.address,
          latitude: selection.latitude,
          longitude: selection.longitude,
        ),
      );
      final savedSelection = selection.copyWith(serverPlaceId: record.id);
      persisted.add(savedSelection);
      _retainPersistedSelection(savedSelection);
    }
    return persisted;
  }

  void _retainPersistedSelection(PlanPlaceSelection savedSelection) {
    final current = _ref.read(selectedPlacesProvider);
    if (!current.any((selection) => selection.id == savedSelection.id)) return;
    _ref.read(selectedPlacesProvider.notifier).state = List.unmodifiable([
      for (final selection in current)
        if (selection.id == savedSelection.id) savedSelection else selection,
    ]);
  }

  void reset() {
    _requestVersion += 1;
    state = const RouteOptimizationState.idle();
  }
}

RouteOptimizationResult _limitResult(
  RouteOptimizationResult result,
  int maxPlaceCount,
) {
  if (!result.isAvailable || result.places.length <= maxPlaceCount) {
    return result;
  }
  return RouteOptimizationResult.success(
    places: result.places.take(maxPlaceCount).toList(growable: false),
    timeline: result.timeline,
    warnings: result.warnings,
    recommendationGroups: result.recommendationGroups,
  );
}
