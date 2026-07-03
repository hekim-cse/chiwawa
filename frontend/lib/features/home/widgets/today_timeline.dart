import 'package:flutter/material.dart';

import '../../../core/mock_data.dart';
import 'schedule_card.dart';

class TodayTimeline extends StatelessWidget {
  const TodayTimeline({
    required this.schedules,
    required this.onFreeTap,
    super.key,
  });

  final List<ScheduleItem> schedules;
  final VoidCallback onFreeTap;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: schedules.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final schedule = schedules[index];

        return ScheduleCard(
          schedule: schedule,
          isLast: index == schedules.length - 1,
          onFreeTap: onFreeTap,
        );
      },
    );
  }
}
