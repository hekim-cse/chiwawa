import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/memorial_models.dart';

class MemorialDateStrip extends StatelessWidget {
  const MemorialDateStrip({
    required this.days,
    required this.selectedDate,
    required this.onSelected,
    super.key,
  });

  final List<MemorialCalendarDay> days;
  final DateTime selectedDate;
  final ValueChanged<DateTime> onSelected;

  @override
  Widget build(BuildContext context) {
    if (days.isEmpty) {
      return const SizedBox(
        height: ChiwawaControlSizes.minimumInteractive,
        child: Align(
          alignment: Alignment.centerLeft,
          child: Text(
            '이 달에는 저장된 사진이 아직 없어요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      );
    }

    return SizedBox(
      height: ChiwawaControlSizes.minimumInteractive,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: days.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final day = days[index];
          final date = day.day;
          final selected = _isSameDay(date, selectedDate);
          return ChoiceChip(
            label: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(_labelFor(date)),
                const SizedBox(width: 5),
                Icon(
                  Icons.photo_rounded,
                  size: 13,
                  color: selected ? Colors.white70 : ChiwawaColors.primary,
                ),
                const SizedBox(width: 2),
                Text(
                  '${day.photoCount}',
                  style: TextStyle(
                    color: selected ? Colors.white70 : ChiwawaColors.primary,
                    fontSize: 11,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
            selected: selected,
            onSelected: (_) => onSelected(date),
            selectedColor: ChiwawaColors.primary,
            backgroundColor: Colors.white,
            side: BorderSide(
              color: selected ? ChiwawaColors.primary : ChiwawaColors.border,
            ),
            labelStyle: TextStyle(
              color: selected ? Colors.white : ChiwawaColors.textPrimary,
              fontWeight: FontWeight.w800,
              fontSize: 13,
            ),
            visualDensity: VisualDensity.compact,
          );
        },
      ),
    );
  }

  bool _isSameDay(DateTime a, DateTime b) {
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }

  String _labelFor(DateTime date) {
    const weekdays = ['월', '화', '수', '목', '금', '토', '일'];
    return '${date.month}월 ${date.day}일 (${weekdays[date.weekday - 1]})';
  }
}
