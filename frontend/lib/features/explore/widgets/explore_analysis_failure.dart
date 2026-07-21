import 'package:flutter/material.dart';

import '../../../app/theme.dart';

class ExploreAnalysisFailure extends StatelessWidget {
  const ExploreAnalysisFailure({
    required this.message,
    required this.canRetry,
    required this.onRetry,
    required this.onChooseAnother,
    super.key,
  });

  final String message;
  final bool canRetry;
  final VoidCallback onRetry;
  final VoidCallback onChooseAnother;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const ValueKey('explore-analysis-failure'),
      padding: const EdgeInsets.all(ChiwawaSpacing.md),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.image_search_rounded,
                color: ChiwawaColors.primary,
                size: 22,
              ),
              SizedBox(width: ChiwawaSpacing.sm),
              Expanded(
                child: Text(
                  '장소를 확인하지 못했어요',
                  style: TextStyle(
                    color: ChiwawaColors.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: ChiwawaSpacing.xs),
          Text(
            '$message 건물이나 간판이 선명한 사진으로 다시 시도해 주세요.',
            style: const TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 13,
              height: 1.45,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: ChiwawaSpacing.md),
          Row(
            children: [
              if (canRetry) ...[
                Expanded(
                  child: OutlinedButton.icon(
                    key: const ValueKey('retry-photo-analysis'),
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh_rounded, size: 18),
                    label: const Text('다시 분석'),
                  ),
                ),
                const SizedBox(width: ChiwawaSpacing.sm),
              ],
              Expanded(
                child: FilledButton.icon(
                  key: const ValueKey('choose-another-photo'),
                  onPressed: onChooseAnother,
                  icon: const Icon(Icons.add_photo_alternate_rounded, size: 18),
                  label: const Text('다른 사진'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
