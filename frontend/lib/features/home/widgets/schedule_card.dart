import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';

class ScheduleCard extends StatelessWidget {
  const ScheduleCard({
    required this.schedule,
    required this.isLast,
    required this.onFreeTap,
    super.key,
  });

  final ScheduleItem schedule;
  final bool isLast;
  final VoidCallback onFreeTap;

  @override
  Widget build(BuildContext context) {
    final isFree = schedule.status == ScheduleStatus.free;
    final completed = schedule.status == ScheduleStatus.completed;

    return Opacity(
      opacity: completed ? 0.5 : 1,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: isFree ? onFreeTap : null,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 48,
              child: Padding(
                padding: const EdgeInsets.only(top: 18),
                child: Text(
                  schedule.time,
                  style: const TextStyle(
                    color: ChiwawaColors.textSecondary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
            _TimelineMarker(status: schedule.status, isLast: isLast),
            const SizedBox(width: 12),
            Expanded(
              child: isFree
                  ? _FreeTimeCard(
                      minutes: schedule.freeMinutes ?? 60,
                      onTap: onFreeTap,
                    )
                  : _PlaceCard(schedule),
            ),
          ],
        ),
      ),
    );
  }
}

class _TimelineMarker extends StatefulWidget {
  const _TimelineMarker({required this.status, required this.isLast});

  final ScheduleStatus status;
  final bool isLast;

  @override
  State<_TimelineMarker> createState() => _TimelineMarkerState();
}

class _TimelineMarkerState extends State<_TimelineMarker>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = switch (widget.status) {
      ScheduleStatus.completed => ChiwawaColors.textMuted,
      ScheduleStatus.ongoing => ChiwawaColors.primary,
      ScheduleStatus.free => ChiwawaColors.primary,
      ScheduleStatus.upcoming => ChiwawaColors.textMuted,
    };

    return SizedBox(
      width: 22,
      height: 96,
      child: Stack(
        alignment: Alignment.topCenter,
        children: [
          if (!widget.isLast)
            Positioned(
              top: 25,
              bottom: 0,
              child: Container(
                width: 1.2,
                decoration: BoxDecoration(
                  border: Border(
                    left: BorderSide(
                      color: widget.status == ScheduleStatus.free
                          ? ChiwawaColors.textMuted
                          : ChiwawaColors.border,
                      width: 1.2,
                    ),
                  ),
                ),
              ),
            ),
          Positioned(
            top: 16,
            child: widget.status == ScheduleStatus.ongoing
                ? FadeTransition(
                    opacity: Tween<double>(begin: 0.45, end: 1).animate(
                      CurvedAnimation(
                        parent: _controller,
                        curve: Curves.easeInOut,
                      ),
                    ),
                    child: _Dot(color: color, filled: true, dashed: false),
                  )
                : _Dot(
                    color: color,
                    filled: widget.status != ScheduleStatus.upcoming,
                    dashed: widget.status == ScheduleStatus.free,
                  ),
          ),
        ],
      ),
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({
    required this.color,
    required this.filled,
    required this.dashed,
  });

  final Color color;
  final bool filled;
  final bool dashed;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: dashed ? 14 : 12,
      height: dashed ? 14 : 12,
      decoration: BoxDecoration(
        color: filled ? color : Colors.white,
        shape: BoxShape.circle,
        border: Border.all(color: color, width: dashed ? 1.5 : 2),
      ),
    );
  }
}

class _PlaceCard extends StatelessWidget {
  const _PlaceCard(this.schedule);

  final ScheduleItem schedule;

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
          Row(
            children: [
              Expanded(
                child: Text(
                  schedule.place ?? '일정',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              _StatusBadge(status: schedule.status),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(
                schedule.transport == '지하철'
                    ? Icons.subway
                    : Icons.directions_walk,
                size: 16,
                color: ChiwawaColors.textMuted,
              ),
              const SizedBox(width: 4),
              Text(
                schedule.transport,
                style: const TextStyle(
                  color: ChiwawaColors.textMuted,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _FreeTimeCard extends StatelessWidget {
  const _FreeTimeCard({required this.minutes, required this.onTap});

  final int minutes;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: ChiwawaColors.primary,
          style: BorderStyle.solid,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              '${minutes ~/ 60}시간 여유가 있어요',
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900),
            ),
          ),
          ElevatedButton(
            onPressed: onTap,
            child: const Text('주변 장소 추천받기'),
          ),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final ScheduleStatus status;

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = switch (status) {
      ScheduleStatus.completed => (
          '완료',
          ChiwawaColors.textSecondary,
          ChiwawaColors.border
        ),
      ScheduleStatus.ongoing => ('이동중', Colors.white, ChiwawaColors.primary),
      ScheduleStatus.upcoming => (
          '예정',
          ChiwawaColors.textSecondary,
          ChiwawaColors.background
        ),
      ScheduleStatus.free => ('추천', Colors.white, ChiwawaColors.primary),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        label,
        style:
            TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w800),
      ),
    );
  }
}
