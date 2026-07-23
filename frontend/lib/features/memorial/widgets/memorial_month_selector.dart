import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/memorial_models.dart';

class MemorialMonthSelector extends StatelessWidget {
  const MemorialMonthSelector({
    required this.month,
    required this.onPrevious,
    required this.onNext,
    super.key,
  });

  final MemorialMonth month;
  final VoidCallback onPrevious;
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: ChiwawaControlSizes.minimumInteractive,
      child: Row(
        children: [
          IconButton(
            key: const ValueKey('memorial-month-previous'),
            onPressed: onPrevious,
            tooltip: '이전 달',
            icon: const Icon(Icons.chevron_left_rounded),
            color: ChiwawaColors.textPrimary,
          ),
          Expanded(
            child: Text(
              '${month.year}년 ${month.month}월',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: ChiwawaColors.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          IconButton(
            key: const ValueKey('memorial-month-next'),
            onPressed: onNext,
            tooltip: '다음 달',
            icon: const Icon(Icons.chevron_right_rounded),
            color: ChiwawaColors.textPrimary,
          ),
        ],
      ),
    );
  }
}
