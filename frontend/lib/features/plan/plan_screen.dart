import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/mock_data.dart';
import '../../core/saved_photo_places.dart';
import 'widgets/place_input_field.dart';
import 'widgets/route_result_card.dart';

final selectedPlacesProvider = StateProvider<List<String>>(
  (ref) => ['메이지 신궁', '하라주쿠', '오모테산도', '시부야'],
);
final routeOptimizingProvider = StateProvider<bool>((ref) => false);
final routeResultVisibleProvider = StateProvider<bool>((ref) => false);

class PlanScreen extends ConsumerWidget {
  const PlanScreen({super.key});

  Future<void> _optimizeRoute(WidgetRef ref) async {
    ref.read(routeOptimizingProvider.notifier).state = true;
    ref.read(routeResultVisibleProvider.notifier).state = false;
    await Future<void>.delayed(const Duration(milliseconds: 900));
    ref.read(routeOptimizingProvider.notifier).state = false;
    ref.read(routeResultVisibleProvider.notifier).state = true;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final places = ref.watch(selectedPlacesProvider);
    final savedPhotoPlaces = ref.watch(savedPhotoPlacesProvider);
    final optimizing = ref.watch(routeOptimizingProvider);
    final showResult = ref.watch(routeResultVisibleProvider);

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
          PlaceInputField(
            places: places,
            onAdd: (place) {
              if (place.trim().isEmpty) return;
              if (places.contains(place.trim())) return;
              ref.read(selectedPlacesProvider.notifier).state = [
                ...places,
                place.trim(),
              ];
              ref.read(routeResultVisibleProvider.notifier).state = false;
            },
            onRemove: (place) {
              ref.read(selectedPlacesProvider.notifier).state =
                  places.where((item) => item != place).toList();
              ref.read(routeResultVisibleProvider.notifier).state = false;
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
                ref.read(routeResultVisibleProvider.notifier).state = false;
                messenger.showSnackBar(
                  SnackBar(content: Text('${place.name} 일정에 추가했어요.')),
                );
              },
            ),
          ],
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: optimizing || places.length < 2
                  ? null
                  : () => _optimizeRoute(ref),
              icon: optimizing
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.4,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.auto_awesome),
              label: Text(optimizing ? '최적 경로 계산 중' : 'AI 경로 최적화'),
            ),
          ),
          if (showResult) ...[
            const SizedBox(height: 22),
            Text(
              '최적 경로 결과',
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 12),
            for (var index = 0; index < routePlaces.length; index++) ...[
              RouteResultCard(
                place: routePlaces[index],
                order: index + 1,
                isLast: index == routePlaces.length - 1,
              ),
              const SizedBox(height: 12),
            ],
            const SizedBox(height: 4),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
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

class _SavedPhotoPlacesSection extends StatelessWidget {
  const _SavedPhotoPlacesSection({
    required this.places,
    required this.selectedPlaces,
    required this.onSelect,
  });

  final List<PhotoSearchResult> places;
  final List<String> selectedPlaces;
  final ValueChanged<PhotoSearchResult> onSelect;

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
                ActionChip(
                  avatar: Icon(
                    selectedPlaces.contains(place.name)
                        ? Icons.check_circle_rounded
                        : Icons.add_location_alt_rounded,
                    color: ChiwawaColors.primary,
                    size: 18,
                  ),
                  label: Text(place.name),
                  onPressed: () => onSelect(place),
                  backgroundColor: ChiwawaColors.secondary,
                  side: const BorderSide(color: ChiwawaColors.border),
                  labelStyle: const TextStyle(
                    color: ChiwawaColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
