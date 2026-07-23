import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/assets/app_images.dart';
import '../../../core/env.dart';
import '../../../core/models/travel_models.dart';

class TodaySchedulePanel extends StatelessWidget {
  const TodaySchedulePanel({
    required this.tripInfo,
    required this.schedules,
    required this.onFreeTap,
    super.key,
  });

  final TripInfo tripInfo;
  final List<ScheduleItem> schedules;
  final VoidCallback onFreeTap;

  @override
  Widget build(BuildContext context) {
    final visibleSchedules = schedules
        .where(
          (schedule) =>
              schedule.place != null || schedule.status == ScheduleStatus.free,
        )
        .take(4)
        .toList(growable: false);
    final nextSchedule = _findNextSchedule(visibleSchedules);
    final remainingSchedules = nextSchedule == null
        ? visibleSchedules
        : visibleSchedules
            .where(
              (schedule) => schedule.identityKey != nextSchedule.identityKey,
            )
            .take(3)
            .toList(growable: false);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (visibleSchedules.isEmpty)
            const Padding(
              padding: EdgeInsets.all(ChiwawaSpacing.sm),
              child: Text(
                '오늘 등록된 일정이 아직 없어요.',
                style: TextStyle(
                  color: ChiwawaColors.textSecondary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          if (nextSchedule != null) ...[
            _NextScheduleCard(
              schedule: nextSchedule,
              onTap:
                  nextSchedule.status == ScheduleStatus.free ? onFreeTap : null,
            ),
            if (remainingSchedules.isNotEmpty) ...[
              const Padding(
                padding: EdgeInsets.fromLTRB(4, 14, 4, 2),
                child: Text(
                  '이후 일정',
                  style: TextStyle(
                    color: ChiwawaColors.textSecondary,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ],
          for (var index = 0; index < remainingSchedules.length; index++)
            _ScheduleSummaryRow(
              key: ValueKey(
                'home-schedule-${remainingSchedules[index].identityKey}-$index',
              ),
              schedule: remainingSchedules[index],
              isLast: index == remainingSchedules.length - 1,
              isPast:
                  remainingSchedules[index].status == ScheduleStatus.completed,
              imageSeed: index + 21,
              onTap: remainingSchedules[index].status == ScheduleStatus.free
                  ? onFreeTap
                  : null,
            ),
        ],
      ),
    );
  }

  ScheduleItem? _findNextSchedule(List<ScheduleItem> schedules) {
    for (final status in [
      ScheduleStatus.ongoing,
      ScheduleStatus.upcoming,
      ScheduleStatus.free,
    ]) {
      for (final schedule in schedules) {
        if (schedule.status == status) return schedule;
      }
    }
    return null;
  }
}

class _NextScheduleCard extends StatelessWidget {
  const _NextScheduleCard({required this.schedule, this.onTap});

  final ScheduleItem schedule;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final statusLabel = switch (schedule.status) {
      ScheduleStatus.ongoing => '진행 중',
      ScheduleStatus.free => '빈 시간',
      _ => '다음 일정',
    };

    return Material(
      key: const ValueKey('home-next-schedule'),
      color: ChiwawaColors.secondary,
      borderRadius: BorderRadius.circular(ChiwawaRadii.control),
      child: InkWell(
        borderRadius: BorderRadius.circular(ChiwawaRadii.control),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(ChiwawaSpacing.sm),
          child: Row(
            children: [
              const SizedBox(
                width: 36,
                height: 40,
                child: Icon(
                  Icons.near_me_rounded,
                  color: ChiwawaColors.primary,
                  size: 21,
                ),
              ),
              const SizedBox(width: ChiwawaSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$statusLabel · ${schedule.time}',
                      style: const TextStyle(
                        color: ChiwawaColors.primary,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: ChiwawaSpacing.xxs),
                    Text(
                      schedule.place ?? '빈 시간 추천',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: ChiwawaColors.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              if (onTap != null)
                const Icon(
                  Icons.chevron_right_rounded,
                  color: ChiwawaColors.primary,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ScheduleSummaryRow extends StatelessWidget {
  const _ScheduleSummaryRow({
    required this.schedule,
    required this.isLast,
    required this.isPast,
    required this.imageSeed,
    this.onTap,
    super.key,
  });

  final ScheduleItem schedule;
  final bool isLast;
  final bool isPast;
  final int imageSeed;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: isPast ? 0.5 : 1,
      child: InkWell(
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.only(bottom: isLast ? 0 : 2),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 48,
                child: Padding(
                  padding: const EdgeInsets.only(top: 11),
                  child: Text(
                    schedule.time,
                    style: const TextStyle(
                      color: ChiwawaColors.textPrimary,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
              _SchedulePin(isLast: isLast),
              const SizedBox(width: 10),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 10),
                  child: Text(
                    schedule.place ?? '빈 시간 추천',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              _PlaceThumbnail(
                seed: imageSeed,
                label: schedule.place ?? '빈 시간 추천',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SchedulePin extends StatelessWidget {
  const _SchedulePin({required this.isLast});

  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 18,
      height: 58,
      child: Stack(
        alignment: Alignment.topCenter,
        children: [
          if (!isLast)
            Positioned(
              top: 23,
              bottom: -4,
              child: Container(width: 1.4, color: ChiwawaColors.border),
            ),
          const Positioned(
            top: 9,
            child: Icon(
              Icons.location_on_rounded,
              color: ChiwawaColors.primary,
              size: 18,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlaceThumbnail extends StatelessWidget {
  const _PlaceThumbnail({required this.seed, required this.label});

  final int seed;
  final String label;

  @override
  Widget build(BuildContext context) {
    if (useApiBackend) return _ThumbnailFallback(label: label);

    return ClipRRect(
      borderRadius: BorderRadius.circular(ChiwawaRadii.control),
      child: SizedBox(
        width: 72,
        height: 54,
        child: Image.asset(
          MockImages.placeThumbnail(seed),
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) =>
              _ThumbnailFallback(label: label),
        ),
      ),
    );
  }
}

class _ThumbnailFallback extends StatelessWidget {
  const _ThumbnailFallback({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final icon = label.contains('스카이')
        ? Icons.cell_tower_rounded
        : label.contains('신주쿠')
            ? Icons.nightlife_rounded
            : label.contains('시부야')
                ? Icons.apartment_rounded
                : Icons.temple_buddhist_rounded;

    return Container(
      color: ChiwawaColors.surfaceMuted,
      child: Icon(icon, color: ChiwawaColors.textSecondary, size: 28),
    );
  }
}
