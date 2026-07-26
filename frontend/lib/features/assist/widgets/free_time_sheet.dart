import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/models/route_planning_models.dart';
import '../../../core/models/travel_models.dart';
import '../../../core/providers/data_providers.dart';
import '../../../shared/widgets/async_value_view.dart';
import '../../../shared/widgets/bottom_sheet_base.dart';
import '../../plan/models/plan_place_selection.dart';
import '../../plan/plan_controller.dart';

void showFreeTimeRecommendSheet(BuildContext context) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => const FreeTimeRecommendSheet(),
  );
}

class FreeTimeRecommendSheet extends ConsumerWidget {
  const FreeTimeRecommendSheet({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendsAsync = ref.watch(freeTimeRecommendsProvider);

    return DraggableScrollableSheet(
      initialChildSize: 0.5,
      minChildSize: 0.36,
      maxChildSize: 0.78,
      expand: false,
      builder: (context, scrollController) {
        return BottomSheetBase(
          children: [
            Expanded(
              child: ListView(
                controller: scrollController,
                children: [
                  Text(
                    '일정 사이에 들를 수 있는 장소예요',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 14),
                  AsyncValueView<List<FreeTimeRecommend>>(
                    value: recommendsAsync,
                    loadingHeight: 120,
                    onRetry: () => ref.invalidate(freeTimeRecommendsProvider),
                    builder: (recommends) => recommends.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.symmetric(vertical: 36),
                            child: Center(
                              child: Text('현재 경로에 삽입 가능한 추천 장소가 없어요.'),
                            ),
                          )
                        : _RecommendationGroups(
                            recommends: recommends,
                            onToggle: (item, isAdded) => _toggleCandidate(
                              context,
                              ref,
                              item,
                              isAdded,
                            ),
                          ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _toggleCandidate(
    BuildContext context,
    WidgetRef ref,
    FreeTimeRecommend item,
    bool isAdded,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      final actions = ref.read(planActionsProvider);
      if (isAdded) {
        final localId =
            'recommendation:${item.recommendation.candidate.placeId}';
        final matches = ref
            .read(selectedPlacesProvider)
            .where((place) => place.id == localId);
        if (matches.isEmpty) {
          throw StateError('일정 후보에서 삭제할 장소를 찾지 못했습니다.');
        }
        actions.removePlace(matches.first);
        messenger.showSnackBar(
          SnackBar(content: Text('${item.name}을 일정 후보에서 삭제했어요.')),
        );
        return;
      }

      // 홈에서 추천을 연 경우 기존 확정 경로를 편집 기준으로 복원한다.
      // 첫 후보 이후에는 기존 freeTime 선택이 있으므로 다시 복원하지 않아
      // 사용자가 여러 카테고리에서 고른 후보를 누적한다.
      final selections = ref.read(selectedPlacesProvider);
      final hasFreeTimeCandidate = selections.any(
        (place) => place.source == PlanPlaceSource.freeTime,
      );
      if (ref.read(routeOptimizationProvider).result == null &&
          !hasFreeTimeCandidate) {
        await _restoreConfirmedRoute(ref, item.dayIndex);
      }

      final added = await actions.addRecommendation(
        item.recommendation,
        reoptimize: false,
      );
      if (!added) {
        throw StateError('이미 일정 후보에 포함된 장소입니다.');
      }
      messenger.showSnackBar(
        SnackBar(content: Text('${item.name}을 일정 후보에 추가했어요.')),
      );
    } catch (error) {
      if (!context.mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text('일정 후보를 변경하지 못했어요: $error')),
      );
    }
  }

  Future<void> _restoreConfirmedRoute(WidgetRef ref, int dayIndex) async {
    final confirmedRoutes = await ref.read(confirmedRoutesProvider.future);
    ConfirmedRoutePlan? confirmed;
    for (final route in confirmedRoutes) {
      if (route.dayIndex == dayIndex) {
        confirmed = route;
        break;
      }
    }
    if (confirmed == null) {
      throw StateError('추천 기준이 된 확정 경로를 찾지 못했습니다.');
    }
    final actions = ref.read(planActionsProvider);
    actions.resetOptimization();
    actions.restoreConfirmedRoute(confirmed);
  }
}

class _RecommendationGroups extends ConsumerStatefulWidget {
  const _RecommendationGroups({
    required this.recommends,
    required this.onToggle,
  });

  final List<FreeTimeRecommend> recommends;
  final Future<void> Function(FreeTimeRecommend item, bool isAdded) onToggle;

  @override
  ConsumerState<_RecommendationGroups> createState() =>
      _RecommendationGroupsState();
}

class _RecommendationGroupsState extends ConsumerState<_RecommendationGroups> {
  String? _selectedCategory;

  @override
  Widget build(BuildContext context) {
    // Backend 순서를 유지하고, 선택된 카테고리의 모든 후보만 표시한다.
    final grouped = <String, List<FreeTimeRecommend>>{};
    for (final item in widget.recommends) {
      final category = item.categoryLabel.trim();
      if (category.isEmpty) {
        throw StateError('빈 시간 추천의 카테고리명이 누락되었습니다.');
      }
      grouped.putIfAbsent(category, () => []).add(item);
    }
    final categories = grouped.keys.toList(growable: false);
    final selectedCategory = categories.contains(_selectedCategory)
        ? _selectedCategory!
        : categories.first;
    final selectedIds = {
      for (final place in ref.watch(selectedPlacesProvider)) place.id,
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              for (var index = 0; index < categories.length; index++) ...[
                _CategoryButton(
                  label: categories[index],
                  selected: categories[index] == selectedCategory,
                  onPressed: () => setState(
                    () => _selectedCategory = categories[index],
                  ),
                ),
                if (index != categories.length - 1) const SizedBox(width: 8),
              ],
            ],
          ),
        ),
        const SizedBox(height: 14),
        for (final item in grouped[selectedCategory]!) ...[
          _RecommendCard(
            item: item,
            isAdded: selectedIds.contains(
              'recommendation:${item.recommendation.candidate.placeId}',
            ),
            onToggle: (isAdded) => widget.onToggle(item, isAdded),
          ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }
}

class _CategoryButton extends StatelessWidget {
  const _CategoryButton({
    required this.label,
    required this.selected,
    required this.onPressed,
  });

  final String label;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      key: ValueKey('free-time-category-$label'),
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        foregroundColor:
            selected ? ChiwawaColors.primary : ChiwawaColors.textPrimary,
        backgroundColor: selected ? ChiwawaColors.secondary : Colors.white,
        side: const BorderSide(color: ChiwawaColors.border),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      ),
      child: Text(
        label,
        style: const TextStyle(fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _RecommendCard extends StatelessWidget {
  const _RecommendCard({
    required this.item,
    required this.isAdded,
    required this.onToggle,
  });

  final FreeTimeRecommend item;
  final bool isAdded;
  final Future<void> Function(bool isAdded) onToggle;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            item.name,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            children: [
              _InfoChip(label: '추가 이동 약 ${item.walk}'),
              _InfoChip(label: '약 ${item.duration} 소요'),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              key: ValueKey('free-time-toggle-${item.id}'),
              onPressed: () async => onToggle(isAdded),
              style: isAdded
                  ? ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: ChiwawaColors.primary,
                      side: const BorderSide(color: ChiwawaColors.primary),
                    )
                  : null,
              child: Text(isAdded ? '일정 후보에서 삭제' : '일정 후보에 추가'),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: ChiwawaColors.background,
        borderRadius: BorderRadius.circular(ChiwawaRadii.round),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: ChiwawaColors.textSecondary,
          fontWeight: FontWeight.w700,
          fontSize: 12,
        ),
      ),
    );
  }
}
