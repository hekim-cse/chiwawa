import 'package:flutter/material.dart';

import '../../../app/theme.dart';

class MemorialDateStrip extends StatelessWidget {
  const MemorialDateStrip({
    required this.dates,
    required this.selectedDate,
    required this.onSelected,
    super.key,
  });

  final List<DateTime> dates;
  final DateTime selectedDate;
  final ValueChanged<DateTime> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: dates.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final date = dates[index];
          final selected = _isSameDay(date, selectedDate);
          return ChoiceChip(
            label: Text(_labelFor(date)),
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
