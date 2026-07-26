import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/models/place_search_models.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/models/route_planning_models.dart';
import '../../core/models/transport_mode.dart';
import '../../core/models/travel_models.dart';
import '../../core/repositories/plan_repository.dart';
import '../../core/saved_photo_places.dart';
import '../../core/services/trip_session_service.dart';
import 'models/plan_itinerary.dart';
import 'models/plan_place_selection.dart';
import 'plan_day_constraints_controller.dart';
import 'plan_place_search_controller.dart';

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
    final timelineStops =
        timeline?.timelineStops ?? const <RouteTimelineStop>[];
    final stops = timelineStops.isEmpty
        ? <PlanItineraryStop>[
            for (var index = 0; index < places.length; index++)
              PlanItineraryStop(
                id: '${places[index].identityKey}-$index',
                startTime: _timeForIndex(index, startTime),
                place: places[index],
              ),
          ]
        : _itineraryFromTimeline(places, timelineStops);
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

List<PlanItineraryStop> _itineraryFromTimeline(
  List<RoutePlace> places,
  List<RouteTimelineStop> timelineStops,
) {
  final placesById = {
    for (final place in places)
      if (place.placeId.isNotEmpty) place.placeId: place,
  };
  var poiIndex = 0;
  final result = <PlanItineraryStop>[];
  for (var index = 0; index < timelineStops.length; index++) {
    final timelineStop = timelineStops[index];
    RoutePlace? place = placesById[timelineStop.placeId];
    if (timelineStop.stopType == 'POI' && place == null) {
      if (poiIndex < places.length) place = places[poiIndex];
      poiIndex += 1;
    }
    place ??= RoutePlace(
      placeId: timelineStop.placeId,
      name: timelineStop.name,
      duration: '',
      transport: '',
      category: timelineStop.stopType == 'START' ? '출발지' : '도착지',
    );
    result.add(
      PlanItineraryStop(
        id: '${timelineStop.stopType}:${timelineStop.placeId}-$index',
        startTime: timelineStop.arrivalTime,
        departureTime: timelineStop.departureTime,
        stayMinutes: timelineStop.stayMinutes,
        stopType: timelineStop.stopType,
        place: place,
      ),
    );
  }
  return result;
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

  Future<bool> saveAndAddSearchedPlace(PlaceSearchCandidate candidate) async {
    final localId = 'place:${candidate.providerPlaceId}';
    final existing = _ref
        .read(selectedPlacesProvider)
        .any((selection) => selection.id == localId);
    if (existing) return false;
    final record = await _ref.read(planRepositoryProvider).saveWantedPlace(
          PlanRoutePlaceInput(
            localId: localId,
            providerPlaceId: candidate.providerPlaceId,
            name: candidate.name,
            address: candidate.formattedAddress,
            latitude: candidate.latitude,
            longitude: candidate.longitude,
          ),
        );
    return _addSelection(
      PlanPlaceSelection(
        id: localId,
        name: candidate.name,
        address: candidate.formattedAddress,
        source: PlanPlaceSource.manual,
        serverPlaceId: record.id,
        providerPlaceId: candidate.providerPlaceId,
        latitude: candidate.latitude,
        longitude: candidate.longitude,
      ),
    );
  }

  Future<bool> addRecommendation(
    RouteRecommendation recommendation, {
    bool reoptimize = true,
  }) async {
    final candidate = recommendation.candidate;
    final localId = 'recommendation:${candidate.placeId}';
    final existing = _ref
        .read(selectedPlacesProvider)
        .any((selection) => selection.id == localId);
    if (existing) return false;
    final record = await _ref.read(planRepositoryProvider).saveWantedPlace(
          PlanRoutePlaceInput(
            localId: localId,
            providerPlaceId: candidate.placeId,
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
        providerPlaceId: candidate.placeId,
        latitude: candidate.latitude,
        longitude: candidate.longitude,
      ),
    );
    if (added && reoptimize) {
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

  void restoreConfirmedRoute(ConfirmedRoutePlan plan) {
    final routeController = _ref.read(routeOptimizationProvider.notifier);
    if (!routeController.restoreConfirmed(plan.dayIndex, plan.result)) return;

    final selections = [
      for (final place in plan.result.places)
        PlanPlaceSelection(
          id: 'restored:${place.placeId}',
          serverPlaceId: place.placeId,
          name: place.name,
          source: PlanPlaceSource.manual,
        ),
    ];
    _ref.read(selectedPlacesProvider.notifier).state =
        List.unmodifiable(selections);
    _ref.read(transportModeProvider.notifier).state =
        plan.result.timeline?.travelMode ?? TransportMode.transit;

    final constraints = _ref.read(planDayConstraintsProvider.notifier);
    constraints.selectStartPlace(plan.dayIndex, plan.startPlace);
    constraints.selectEndPlace(plan.dayIndex, plan.endPlace);
    final placeSearch = _ref.read(planPlaceSearchProvider.notifier);
    placeSearch.selectPlace(
      PlanPlaceSearchKey(day: plan.dayIndex, role: PlanPlaceRole.start),
      plan.startPlace,
    );
    placeSearch.selectPlace(
      PlanPlaceSearchKey(day: plan.dayIndex, role: PlanPlaceRole.end),
      plan.endPlace,
    );
    final timeline = plan.result.timeline;
    if (timeline != null) {
      constraints.updateStartTime(plan.dayIndex, timeline.plannedStartTime);
      constraints.updateEndTime(plan.dayIndex, timeline.plannedEndTime);
    }

    final itinerary = _ref.read(planItineraryProvider.notifier);
    itinerary.selectDay(plan.dayIndex);
    itinerary.replaceCurrentDay(
      plan.result.places,
      timeline: plan.result.timeline,
    );
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
  final Set<int> _restoredConfirmedDays = {};

  bool canRestoreConfirmed(int dayIndex) =>
      state.status == AiJobStatus.idle &&
      !_restoredConfirmedDays.contains(dayIndex);

  bool restoreConfirmed(int dayIndex, RouteOptimizationResult result) {
    if (!canRestoreConfirmed(dayIndex) || result.timeline == null) {
      return false;
    }
    _restoredConfirmedDays.add(dayIndex);
    state = RouteOptimizationState.done(result);
    return true;
  }

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
      _mergeSavedPhotoPlacesIntoSelections();
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
                    providerPlaceId: selection.providerPlaceId,
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
              maxPlaceCount: null,
              startPlace: dayConstraint.startPlace!,
              endPlace: dayConstraint.endPlace!,
            ),
          );
      if (requestVersion != _requestVersion) return;
      final filteredResult = _excludeSelectedRecommendations(
        result,
        selections,
      );
      state = RouteOptimizationState.done(filteredResult);
      if (!filteredResult.isAvailable) {
        _ref.read(planItineraryProvider.notifier).clearCurrentDay();
        return;
      }
      _ref.read(planItineraryProvider.notifier).replaceCurrentDay(
            filteredResult.places,
            startTime: dayConstraint.startTime,
            timeline: filteredResult.timeline,
          );
    } catch (error) {
      if (requestVersion != _requestVersion) return;
      state = RouteOptimizationState.failed(
        mapApiErrorToMessage(error),
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
          providerPlaceId: selection.providerPlaceId,
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

  void _mergeSavedPhotoPlacesIntoSelections() {
    final current = _ref.read(selectedPlacesProvider);
    final currentIds = current.map((selection) => selection.id).toSet();
    final additions = [
      for (final place in _ref.read(savedPhotoPlacesProvider))
        if (currentIds.add(PlanPlaceSelection.photoIdentity(place)))
          PlanPlaceSelection.fromPhoto(place),
    ];
    if (additions.isEmpty) return;
    _ref.read(selectedPlacesProvider.notifier).state =
        List.unmodifiable([...current, ...additions]);
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
