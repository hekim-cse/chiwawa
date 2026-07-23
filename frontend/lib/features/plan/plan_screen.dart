import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/confirmed_route.dart';
import '../../core/models/travel_models.dart';
import '../../core/providers/data_providers.dart';
import '../../core/saved_photo_places.dart';
import '../../shared/widgets/app_list_group.dart';
import '../../shared/widgets/app_page_header.dart';
import '../../shared/widgets/app_section_header.dart';
import '../../shared/widgets/app_viewport.dart';
import 'models/plan_itinerary.dart';
import 'plan_controller.dart';
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

class PlanScreen extends ConsumerWidget {
  const PlanScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final places = ref.watch(selectedPlacesProvider);
    final savedPhotoPlaces = ref.watch(savedPhotoPlacesProvider);
    final routeState = ref.watch(routeOptimizationProvider);
    final itinerary = ref.watch(planItineraryProvider);
    final preference = ref.watch(travelPreferenceProvider);
    final transportMode = ref.watch(transportModeProvider);
    final actions = ref.read(planActionsProvider);
    final tripInfo = ref.watch(tripInfoProvider).valueOrNull;

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
            onAdd: actions.addPlace,
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
          const SizedBox(height: ChiwawaSpacing.md),
          RouteOptimizationSection(
            state: routeState,
            canOptimize: places.length >= 2,
            onOptimize: () => actions.optimizeRoute(transportMode),
            transportMode: transportMode,
            itinerary: itinerary.currentStops,
            onMove: ref.read(planItineraryProvider.notifier).move,
            onEditTime: (stop) => _editTime(context, ref, stop),
            onDelete: (stop) => _deleteStop(context, ref, stop),
            onConfirm: () => _confirmRoute(
              context,
              ref,
              itinerary.currentStops.map((stop) => stop.place).toList(),
            ),
          ),
          const SizedBox(height: ChiwawaSpacing.section),
          TravelPreferenceSection(
            preference: preference,
            onThemeChanged: actions.updateTheme,
            onPaceChanged: actions.updatePace,
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

  void _confirmRoute(
    BuildContext context,
    WidgetRef ref,
    List<RoutePlace> places,
  ) {
    ref.read(confirmedRouteProvider.notifier).confirm(places);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('이 일정으로 확정했어요.')),
    );
  }
}
