import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
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
                        : Column(
                            children: [
                        for (final item in recommends) ...[
                          _RecommendCard(
                            item: item,
                            onAdd: () {
                              ref.read(planActionsProvider).addPlace(
                                    item.name,
                                    source: PlanPlaceSource.freeTime,
                                  );
                              final messenger = ScaffoldMessenger.of(context);
                              Navigator.of(context).pop();
                              messenger.showSnackBar(
                                SnackBar(
                                  content: Text('${item.name}을 일정 후보에 추가했어요.'),
                                ),
                              );
                            },
                            onDismiss: () => Navigator.of(context).pop(),
                          ),
                          const SizedBox(height: 12),
                        ],
                            ],
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
}

class _RecommendCard extends StatelessWidget {
  const _RecommendCard({
    required this.item,
    required this.onAdd,
    required this.onDismiss,
  });

  final FreeTimeRecommend item;
  final VoidCallback onAdd;
  final VoidCallback onDismiss;

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
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  onPressed: onAdd,
                  child: const Text('일정 후보에 추가'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextButton(
                  onPressed: onDismiss,
                  child: const Text(
                    '나중에',
                    style: TextStyle(color: ChiwawaColors.textSecondary),
                  ),
                ),
              ),
            ],
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
