import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/mock_data.dart';
import '../../../shared/widgets/bottom_sheet_base.dart';

void showFreeTimeRecommendSheet(BuildContext context) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => const FreeTimeRecommendSheet(),
  );
}

class FreeTimeRecommendSheet extends StatelessWidget {
  const FreeTimeRecommendSheet({super.key});

  @override
  Widget build(BuildContext context) {
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
                    '지금 1시간 여유가 있어요',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 14),
                  for (final item in freeTimeRecommends) ...[
                    _RecommendCard(item: item),
                    const SizedBox(height: 12),
                  ],
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
  const _RecommendCard({required this.item});

  final FreeTimeRecommend item;

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
          Text(
            item.name,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            children: [
              _InfoChip(label: '도보 ${item.walk}'),
              _InfoChip(label: '약 ${item.duration} 소요'),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('일정 추가'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text(
                    '패스',
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
        borderRadius: BorderRadius.circular(99),
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
