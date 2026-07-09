import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/confirmed_route.dart';
import '../../core/models/travel_models.dart';
import '../../core/repositories/plan_repository.dart';
import '../../core/saved_photo_places.dart';
import 'widgets/place_input_field.dart';
import 'widgets/route_result_card.dart';

final selectedPlacesProvider = StateProvider<List<String>>(
  (ref) => ref.watch(planRepositoryProvider).defaultSelectedPlaces,
);
final travelPreferenceProvider = StateProvider<TravelPreference>(
  (ref) => const TravelPreference(),
);
final routeOptimizationProvider = StateProvider<RouteOptimizationState>(
  (ref) => const RouteOptimizationState.idle(),
);

class PlanScreen extends ConsumerWidget {
  const PlanScreen({super.key});

  Future<void> _optimizeRoute(WidgetRef ref) async {
    final places = ref.read(selectedPlacesProvider);
    final preference = ref.read(travelPreferenceProvider);
    final notifier = ref.read(routeOptimizationProvider.notifier);

    notifier.state = const RouteOptimizationState.pending();
    await Future<void>.delayed(const Duration(milliseconds: 180));
    notifier.state = const RouteOptimizationState.running();

    try {
      final routePlaces = await ref.read(planRepositoryProvider).optimizeRoute(
            places,
            preference,
          );
      notifier.state = RouteOptimizationState.done(routePlaces);
    } catch (_) {
      notifier.state = const RouteOptimizationState.failed(
        '경로 최적화에 실패했어요. 다시 시도해 주세요.',
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final places = ref.watch(selectedPlacesProvider);
    final savedPhotoPlaces = ref.watch(savedPhotoPlacesProvider);
    final routeState = ref.watch(routeOptimizationProvider);
    final preference = ref.watch(travelPreferenceProvider);

    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
        children: [
          Text(
            'AI 일정 설계',
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 6),
          const Text(
            '가고 싶은 장소를 넣으면 이동 동선을 자동으로 정리해요.',
            style: TextStyle(color: ChiwawaColors.textSecondary),
          ),
          const SizedBox(height: 18),
          _TravelPreferenceSection(
            preference: preference,
            onThemeChanged: (theme, selected) {
              final nextThemes = {...preference.themes};
              if (selected) {
                nextThemes.add(theme);
              } else if (nextThemes.length > 1) {
                nextThemes.remove(theme);
              }

              ref.read(travelPreferenceProvider.notifier).state =
                  preference.copyWith(themes: nextThemes);
              ref.read(routeOptimizationProvider.notifier).state =
                  const RouteOptimizationState.idle();
            },
            onPaceChanged: (pace) {
              ref.read(travelPreferenceProvider.notifier).state =
                  preference.copyWith(pace: pace);
              ref.read(routeOptimizationProvider.notifier).state =
                  const RouteOptimizationState.idle();
            },
          ),
          const SizedBox(height: 16),
          PlaceInputField(
            places: places,
            onAdd: (place) {
              if (place.trim().isEmpty) return;
              if (places.contains(place.trim())) return;
              ref.read(selectedPlacesProvider.notifier).state = [
                ...places,
                place.trim(),
              ];
              ref.read(routeOptimizationProvider.notifier).state =
                  const RouteOptimizationState.idle();
            },
            onRemove: (place) {
              ref.read(selectedPlacesProvider.notifier).state =
                  places.where((item) => item != place).toList();
              ref.read(routeOptimizationProvider.notifier).state =
                  const RouteOptimizationState.idle();
            },
          ),
          if (savedPhotoPlaces.isNotEmpty) ...[
            const SizedBox(height: 16),
            _SavedPhotoPlacesSection(
              places: savedPhotoPlaces,
              selectedPlaces: places,
              onSelect: (place) {
                final messenger = ScaffoldMessenger.of(context)
                  ..hideCurrentSnackBar();

                if (places.contains(place.name)) {
                  messenger.showSnackBar(
                    SnackBar(content: Text('${place.name} 이미 일정에 있어요.')),
                  );
                  return;
                }

                ref.read(selectedPlacesProvider.notifier).state = [
                  ...places,
                  place.name,
                ];
                ref.read(routeOptimizationProvider.notifier).state =
                    const RouteOptimizationState.idle();
                messenger.showSnackBar(
                  SnackBar(content: Text('${place.name} 일정에 추가했어요.')),
                );
              },
              onRemove: (place) {
                ref.read(savedPhotoPlacesProvider.notifier).removePlace(place);
                ScaffoldMessenger.of(context)
                  ..hideCurrentSnackBar()
                  ..showSnackBar(
                    SnackBar(content: Text('${place.name} 저장 목록에서 삭제했어요.')),
                  );
              },
            ),
          ],
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: routeState.isWorking || places.length < 2
                  ? null
                  : () => _optimizeRoute(ref),
              icon: routeState.isWorking
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.4,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.auto_awesome),
              label: Text(
                routeState.isWorking ? '최적 경로 계산 중' : 'AI 경로 최적화',
              ),
            ),
          ),
          if (routeState.status == AiJobStatus.failed) ...[
            const SizedBox(height: 16),
            _RouteFailureCard(
              message: routeState.message ?? '경로 최적화에 실패했어요.',
              onRetry: () => _optimizeRoute(ref),
            ),
          ],
          if (routeState.status == AiJobStatus.done) ...[
            const SizedBox(height: 22),
            Text(
              '최적 경로 결과',
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 12),
            for (var index = 0; index < routeState.places.length; index++) ...[
              RouteResultCard(
                place: routeState.places[index],
                order: index + 1,
                isLast: index == routeState.places.length - 1,
              ),
              const SizedBox(height: 12),
            ],
            const SizedBox(height: 4),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                key: const ValueKey('confirm-route-button'),
                onPressed: () {
                  ref
                      .read(confirmedRouteProvider.notifier)
                      .confirm(routeState.places);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('이 일정으로 확정했어요.')),
                  );
                },
                child: const Text('이 일정으로 확정하기'),
              ),
            ),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _TravelPreferenceSection extends StatelessWidget {
  const _TravelPreferenceSection({
    required this.preference,
    required this.onThemeChanged,
    required this.onPaceChanged,
  });

  final TravelPreference preference;
  final void Function(TravelTheme theme, bool selected) onThemeChanged;
  final ValueChanged<TravelPace> onPaceChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'AI 추천 조건',
            style: TextStyle(
              color: ChiwawaColors.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            '원하는 여행 분위기를 선택지로만 골라요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final theme in TravelTheme.values)
                FilterChip(
                  label: Text(theme.label),
                  selected: preference.themes.contains(theme),
                  onSelected: (selected) => onThemeChanged(theme, selected),
                  selectedColor: ChiwawaColors.primary,
                  checkmarkColor: Colors.white,
                  labelStyle: TextStyle(
                    color: preference.themes.contains(theme)
                        ? Colors.white
                        : ChiwawaColors.textSecondary,
                    fontWeight: FontWeight.w800,
                  ),
                  side: const BorderSide(color: ChiwawaColors.border),
                ),
            ],
          ),
          const SizedBox(height: 14),
          SegmentedButton<TravelPace>(
            segments: [
              for (final pace in TravelPace.values)
                ButtonSegment(
                  value: pace,
                  label: Text(pace.label),
                ),
            ],
            selected: {preference.pace},
            onSelectionChanged: (selection) => onPaceChanged(selection.first),
          ),
        ],
      ),
    );
  }
}

class _RouteFailureCard extends StatelessWidget {
  const _RouteFailureCard({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.error_outline_rounded,
            color: ChiwawaColors.primary,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: ChiwawaColors.textSecondary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          TextButton(
            onPressed: onRetry,
            child: const Text('다시 시도'),
          ),
        ],
      ),
    );
  }
}

class _SavedPhotoPlacesSection extends StatelessWidget {
  const _SavedPhotoPlacesSection({
    required this.places,
    required this.selectedPlaces,
    required this.onSelect,
    required this.onRemove,
  });

  final List<PhotoSearchResult> places;
  final List<String> selectedPlaces;
  final ValueChanged<PhotoSearchResult> onSelect;
  final ValueChanged<PhotoSearchResult> onRemove;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.camera_alt_rounded,
                color: ChiwawaColors.primary,
                size: 20,
              ),
              SizedBox(width: 8),
              Text(
                '사진으로 저장한 장소',
                style: TextStyle(
                  color: ChiwawaColors.textPrimary,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            '사진 탐색에서 찾은 장소를 일정 후보로 바로 넣어보세요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final place in places)
                _SavedPhotoPlaceChip(
                  place: place,
                  selected: selectedPlaces.contains(place.name),
                  onSelect: () => onSelect(place),
                  onRemove: () => onRemove(place),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SavedPhotoPlaceChip extends StatelessWidget {
  const _SavedPhotoPlaceChip({
    required this.place,
    required this.selected,
    required this.onSelect,
    required this.onRemove,
  });

  final PhotoSearchResult place;
  final bool selected;
  final VoidCallback onSelect;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: ChiwawaColors.secondary,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(99),
        side: const BorderSide(color: ChiwawaColors.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            key: ValueKey('select-saved-place-${place.name}'),
            onTap: onSelect,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(10, 7, 6, 7),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    selected
                        ? Icons.check_circle_rounded
                        : Icons.add_location_alt_rounded,
                    color: ChiwawaColors.primary,
                    size: 17,
                  ),
                  const SizedBox(width: 5),
                  Text(
                    place.name,
                    style: const TextStyle(
                      color: ChiwawaColors.textPrimary,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
          ),
          InkWell(
            key: ValueKey('remove-saved-place-${place.name}'),
            onTap: onRemove,
            child: const Padding(
              padding: EdgeInsets.fromLTRB(4, 7, 9, 7),
              child: Icon(
                Icons.close_rounded,
                color: ChiwawaColors.primary,
                size: 16,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
