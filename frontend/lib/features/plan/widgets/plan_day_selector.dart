import 'package:flutter/material.dart';

import '../../../app/theme.dart';

class PlanDaySelector extends StatelessWidget {
  const PlanDaySelector({
    required this.selectedDay,
    required this.onSelected,
    this.dayCount = 4,
    super.key,
  });

  final int selectedDay;
  final int dayCount;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: ChiwawaColors.border)),
      ),
      child: SizedBox(
        height: 46,
        child: Row(
          children: [
            for (var day = 1; day <= dayCount; day++)
              Expanded(
                child: InkWell(
                  key: ValueKey('plan-day-$day'),
                  onTap: () => onSelected(day),
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      border: Border(
                        bottom: BorderSide(
                          color: selectedDay == day
                              ? ChiwawaColors.primary
                              : Colors.transparent,
                          width: 2,
                        ),
                      ),
                    ),
                    child: Center(
                      child: Text(
                        '$day일차',
                        maxLines: 1,
                        style:
                            Theme.of(context).textTheme.labelMedium?.copyWith(
                                  color: selectedDay == day
                                      ? ChiwawaColors.primary
                                      : ChiwawaColors.textSecondary,
                                  fontWeight: selectedDay == day
                                      ? FontWeight.w800
                                      : FontWeight.w600,
                                ),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
