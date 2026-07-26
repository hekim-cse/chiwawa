import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/api/api_exception.dart';
import '../../core/confirmed_route.dart';
import '../../core/models/place_search_models.dart';
import '../../core/models/route_planning_models.dart';
import '../../core/models/travel_models.dart';
import '../../core/providers/data_providers.dart';
import '../../core/repositories/plan_repository.dart';
import '../../core/saved_photo_places.dart';
import '../../shared/widgets/app_list_group.dart';
import '../../shared/widgets/app_page_header.dart';
import '../../shared/widgets/app_section_header.dart';
import '../../shared/widgets/app_viewport.dart';
import 'models/plan_itinerary.dart';
import 'plan_controller.dart';
import 'plan_day_constraints_controller.dart';
import 'plan_place_search_controller.dart';
import 'widgets/plan_day_constraint_section.dart';
import 'widgets/plan_day_selector.dart';
import 'widgets/plan_transport_mode_section.dart';
import 'widgets/place_input_field.dart';
import 'widgets/route_optimization_section.dart';
import 'widgets/saved_photo_places_section.dart';
import 'widgets/travel_preference_section.dart';

export 'plan_controller.dart'
    show
        selectedPlacesProvider,
        travelPreferenceProvider,
        transportModeProvider,
        routeOptimizationProvider,
        planItineraryProvider,
        planActionsProvider;
export 'plan_day_constraints_controller.dart' show planDayConstraintsProvider;
export 'plan_place_search_controller.dart'
    show
        PlanPlaceRole,
        PlanPlaceSearchKey,
        PlanPlaceSearchState,
        PlanPlaceSearchStatus,
        planPlaceSearchProvider;

class PlanScreen extends ConsumerWidget {
  const PlanScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final places = ref.watch(selectedPlacesProvider);
    final savedPhotoPlaces = ref.watch(savedPhotoPlacesProvider);
    final routeState = ref.watch(routeOptimizationProvider);
    final itinerary = ref.watch(planItineraryProvider);
    final dayConstraints = ref.watch(planDayConstraintsProvider);
    final dayConstraint = dayConstraints.forDay(itinerary.selectedDay);
    final placeSearchStates = ref.watch(planPlaceSearchProvider);
    final startSearchKey = PlanPlaceSearchKey(
      day: itinerary.selectedDay,
      role: PlanPlaceRole.start,
    );
    final endSearchKey = PlanPlaceSearchKey(
      day: itinerary.selectedDay,
      role: PlanPlaceRole.end,
    );
    final visitSearchKey = PlanPlaceSearchKey(
      day: itinerary.selectedDay,
      role: PlanPlaceRole.visit,
    );
    final preference = ref.watch(travelPreferenceProvider);
    final transportMode = ref.watch(transportModeProvider);
    final actions = ref.read(planActionsProvider);
    final tripInfo = ref.watch(tripInfoProvider).valueOrNull;
    final confirmedRoutes = ref.watch(confirmedRoutesProvider).valueOrNull;
    final routeController = ref.read(routeOptimizationProvider.notifier);
    if (confirmedRoutes != null &&
        confirmedRoutes.isNotEmpty &&
        routeController.canRestoreConfirmed(confirmedRoutes.first.dayIndex) &&
        itinerary.currentStops.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(planActionsProvider).restoreConfirmedRoute(
              confirmedRoutes.first,
            );
      });
    }

    return SafeArea(
      child: ListView(
        key: const ValueKey('plan-scroll'),
        scrollCacheExtent: const ScrollCacheExtent.pixels(5000),
        padding: AppLayout.pageInsets(context),
        children: [
          const AppPageHeader(
            title: 'AI 일정 설계',
            subtitle: '날짜별 장소와 이동 동선을 한 화면에서 편집하세요.',
          ),
          const SizedBox(height: 18),
          AppListGroup(
            children: [
              AppListRow(
                title: tripInfo?.tripName ?? '현재 여행',
                subtitle: [tripInfo?.city ?? '', tripInfo?.period ?? '']
                    .where((value) => value.trim().isNotEmpty)
                    .join(' · '),
                leading: const AppLeadingIcon(icon: Icons.luggage_rounded),
                trailing: const Icon(
                  Icons.swap_horiz_rounded,
                  color: ChiwawaColors.primary,
                ),
                showDivider: false,
                onTap: () => context.go('/trips'),
              ),
            ],
          ),
          const SizedBox(height: ChiwawaSpacing.md),
          PlanDaySelector(
            selectedDay: itinerary.selectedDay,
            onSelected: (day) => _selectDay(ref, day),
          ),
          const SizedBox(height: ChiwawaSpacing.lg),
          PlanDayConstraintSection(
            key: ValueKey('plan-day-constraint-${itinerary.selectedDay}'),
            day: itinerary.selectedDay,
            constraint: dayConstraint,
            startSearchState: placeSearchStates.forKey(startSearchKey),
            endSearchState: placeSearchStates.forKey(endSearchKey),
            onStartQueryChanged: (value) => _updatePlaceQuery(
              ref,
              key: startSearchKey,
              value: value,
            ),
            onStartPlaceSelected: (place) => _selectConstraintPlace(
              ref,
              key: startSearchKey,
              place: place,
            ),
            onStartRetry: () => unawaited(
              ref.read(planPlaceSearchProvider.notifier).retry(startSearchKey),
            ),
            onStartTimeChanged: (value) => _updateDayConstraint(
              ref,
              (controller) => controller.updateStartTime(
                itinerary.selectedDay,
                value,
              ),
            ),
            onEndQueryChanged: (value) => _updatePlaceQuery(
              ref,
              key: endSearchKey,
              value: value,
            ),
            onEndPlaceSelected: (place) => _selectConstraintPlace(
              ref,
              key: endSearchKey,
              place: place,
            ),
            onEndRetry: () => unawaited(
              ref.read(planPlaceSearchProvider.notifier).retry(endSearchKey),
            ),
            onEndTimeChanged: (value) => _updateDayConstraint(
              ref,
              (controller) => controller.updateEndTime(
                itinerary.selectedDay,
                value,
              ),
            ),
          ),
          const SizedBox(height: ChiwawaSpacing.section),
          AppSectionHeader(
            title: '등록 장소',
            description: '이번 날짜에 방문할 장소를 확인하고 더해 보세요.',
            trailing: Text(
              '${places.length}곳',
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: ChiwawaColors.primary,
                    fontWeight: FontWeight.w800,
                  ),
            ),
          ),
          const SizedBox(height: ChiwawaSpacing.sm),
          PlaceInputField(
            places: places,
            searchState: placeSearchStates.forKey(visitSearchKey),
            onQueryChanged: (value) => _updatePlaceQuery(
              ref,
              key: visitSearchKey,
              value: value,
            ),
            onPlaceSelected: (place) => unawaited(
              _saveSearchedPlace(
                context,
                ref,
                actions,
                visitSearchKey,
                place,
              ),
            ),
            onRetry: () => unawaited(
              ref.read(planPlaceSearchProvider.notifier).retry(visitSearchKey),
            ),
            onRemove: actions.removePlace,
          ),
          if (savedPhotoPlaces.isNotEmpty) ...[
            const SizedBox(height: 16),
            SavedPhotoPlacesSection(
              places: savedPhotoPlaces,
              selectedPlaces: places,
              onSelect: (place) => _addSavedPlace(
                context,
                actions,
                place,
              ),
              onRemove: (place) => _removeSavedPlace(context, ref, place),
            ),
          ],
          const SizedBox(height: ChiwawaSpacing.section),
          PlanTransportModeSection(
            selected: transportMode,
            onSelected: actions.updateTransportMode,
          ),
          const SizedBox(height: ChiwawaSpacing.section),
          TravelPreferenceSection(
            preference: preference,
            onThemeChanged: actions.updateTheme,
            onPaceChanged: actions.updatePace,
          ),
          const SizedBox(height: ChiwawaSpacing.md),
          RouteOptimizationSection(
            state: routeState,
            canOptimize: places.length >= 2 && dayConstraint.isValid,
            onOptimize: () => actions.optimizeRoute(transportMode),
            transportMode: transportMode,
            itinerary: itinerary.currentStops,
            onMove: ref.read(planItineraryProvider.notifier).move,
            onEditTime: (stop) => _editTime(context, ref, stop),
            onDelete: (stop) => _deleteStop(context, ref, stop),
            onConfirm: () => _confirmRoute(
              context,
              ref,
              routeState.result,
              itinerary.currentStops,
            ),
            onAddRecommendation: (recommendation) =>
                _addRecommendation(context, actions, recommendation),
          ),
          const SizedBox(height: ChiwawaSpacing.xl),
        ],
      ),
    );
  }

  void _selectDay(WidgetRef ref, int day) {
    ref.read(planItineraryProvider.notifier).selectDay(day);
    ref.read(routeOptimizationProvider.notifier).reset();
  }

  void _updateDayConstraint(
    WidgetRef ref,
    void Function(PlanDayConstraintsController controller) update,
  ) {
    update(ref.read(planDayConstraintsProvider.notifier));
    ref.read(planActionsProvider).resetOptimization();
  }

  void _updatePlaceQuery(
    WidgetRef ref, {
    required PlanPlaceSearchKey key,
    required String value,
    String? cityBias,
  }) {
    final constraints = ref.read(planDayConstraintsProvider);
    final constraint = constraints.forDay(key.day);
    final selected = switch (key.role) {
      PlanPlaceRole.start => constraint.startPlace,
      PlanPlaceRole.end => constraint.endPlace,
      PlanPlaceRole.visit => null,
    };
    if (selected != null && value != selected.name) {
      _updateDayConstraint(
        ref,
        (controller) {
          switch (key.role) {
            case PlanPlaceRole.start:
              controller.clearStartPlace(key.day);
            case PlanPlaceRole.end:
              controller.clearEndPlace(key.day);
            case PlanPlaceRole.visit:
              return;
          }
        },
      );
    }
    ref.read(planPlaceSearchProvider.notifier).updateQuery(
          key,
          value,
          cityBias: cityBias,
        );
  }

  void _selectConstraintPlace(
    WidgetRef ref, {
    required PlanPlaceSearchKey key,
    required PlaceSearchCandidate place,
  }) {
    _updateDayConstraint(
      ref,
      (controller) => key.role == PlanPlaceRole.start
          ? controller.selectStartPlace(key.day, place)
          : controller.selectEndPlace(key.day, place),
    );
    ref.read(planPlaceSearchProvider.notifier).selectPlace(key, place);
  }

  Future<void> _editTime(
    BuildContext context,
    WidgetRef ref,
    PlanItineraryStop stop,
  ) async {
    final parts = stop.startTime.split(':');
    final initial = TimeOfDay(
      hour: int.tryParse(parts.first) ?? 9,
      minute: parts.length > 1 ? int.tryParse(parts[1]) ?? 0 : 0,
    );
    final picked = await showTimePicker(
      context: context,
      initialTime: initial,
      helpText: '방문 시간 선택',
    );
    if (picked == null || !context.mounted) return;
    final value = '${picked.hour.toString().padLeft(2, '0')}:'
        '${picked.minute.toString().padLeft(2, '0')}';
    ref.read(planItineraryProvider.notifier).updateTime(stop.id, value);
  }

  void _deleteStop(
    BuildContext context,
    WidgetRef ref,
    PlanItineraryStop stop,
  ) {
    ref.read(planItineraryProvider.notifier).remove(stop.id);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
          SnackBar(content: Text('${stop.place.name}을(를) 일정에서 삭제했어요.')));
  }

  void _addSavedPlace(
    BuildContext context,
    PlanActions actions,
    PhotoSearchResult place,
  ) {
    final added = actions.addSavedPlace(place);
    final messenger = ScaffoldMessenger.of(context)..hideCurrentSnackBar();
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          added ? '${place.name} 일정에 추가했어요.' : '${place.name} 이미 일정에 있어요.',
        ),
      ),
    );
  }

  Future<void> _saveSearchedPlace(
    BuildContext context,
    WidgetRef ref,
    PlanActions actions,
    PlanPlaceSearchKey searchKey,
    PlaceSearchCandidate place,
  ) async {
    try {
      final added = await actions.saveAndAddSearchedPlace(place);
      if (!context.mounted) return;
      if (added) {
        ref
            .read(planPlaceSearchProvider.notifier)
            .selectPlace(searchKey, place);
      }
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(
              added ? '${place.name} 서버에 저장했어요.' : '${place.name} 이미 일정에 있어요.',
            ),
          ),
        );
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(content: Text(mapApiErrorToMessage(error))),
        );
      if (error is ApiException && error.isNotFound) {
        context.go('/trips');
      }
    }
  }

  Future<bool> _addRecommendation(
    BuildContext context,
    PlanActions actions,
    RouteRecommendation recommendation,
  ) async {
    try {
      final added = await actions.addRecommendation(recommendation);
      if (!context.mounted) return added;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(
              added
                  ? '${recommendation.candidate.name} 장소를 추가하고 일정을 다시 계산했어요.'
                  : '${recommendation.candidate.name} 이미 일정에 있어요.',
            ),
          ),
        );
      return added;
    } catch (_) {
      if (!context.mounted) return false;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(content: Text('추천 장소를 추가하지 못했어요. 다시 시도해 주세요.')),
        );
      return false;
    }
  }

  void _removeSavedPlace(
    BuildContext context,
    WidgetRef ref,
    PhotoSearchResult place,
  ) {
    ref.read(savedPhotoPlacesProvider.notifier).removePlace(place);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(content: Text('${place.name} 저장 목록에서 삭제했어요.')),
      );
  }

  Future<void> _confirmRoute(
    BuildContext context,
    WidgetRef ref,
    RouteOptimizationResult? result,
    List<PlanItineraryStop> stops,
  ) async {
    if (result == null || result.timeline == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('확정할 경로 타임라인이 없어요.')),
      );
      return;
    }
    try {
      await ref.read(planRepositoryProvider).confirmRoute(result);
      ref.read(confirmedRouteProvider.notifier).confirm(
            stops
                .where((stop) => stop.stopType == 'POI')
                .map((stop) => stop.place)
                .toList(growable: false),
          );
      // 확정 직후 홈·확정 일정만 새로 조회한다.
      // currentTripRevision을 변경하면 선택 장소와 방금 계산한
      // 최적화 결과까지 초기화되어 이전 확정 경로가 복원될 수 있다.
      ref.invalidate(confirmedRoutesProvider);
      ref.invalidate(todaySchedulesProvider);
      ref.invalidate(homeDataProvider);
      ref.invalidate(freeTimeRecommendsProvider);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('이 일정으로 확정했어요.')),
      );
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(mapApiErrorToMessage(error))),
      );
    }
  }
}
