import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../shared/widgets/app_section_header.dart';
import '../models/plan_itinerary.dart';
import 'route_map_overview.dart';

class PlanItineraryWorkspace extends StatelessWidget {
  const PlanItineraryWorkspace({
    required this.stops,
    required this.onConfirm,
    this.onMove,
    this.onEditTime,
    this.onDelete,
    super.key,
  });

  final List<PlanItineraryStop> stops;
  final void Function(int fromIndex, int toIndex)? onMove;
  final ValueChanged<PlanItineraryStop>? onEditTime;
  final ValueChanged<PlanItineraryStop>? onDelete;
  final VoidCallback onConfirm;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionHeader(
          title: '최적 경로 결과',
          description: '지도 번호와 일정 순서가 함께 바뀌어요.',
          trailing: Text(
            '${stops.length}곳',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: ChiwawaColors.textSecondary,
                ),
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        RouteMapOverview(stops: stops),
        const SizedBox(height: ChiwawaSpacing.sm),
        _ItinerarySummary(stops: stops),
        const SizedBox(height: ChiwawaSpacing.lg),
        const AppSectionHeader(title: '일정 타임라인'),
        const SizedBox(height: ChiwawaSpacing.sm),
        Material(
          color: Colors.transparent,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: ChiwawaSpacing.xs),
            child: Column(
              children: [
                for (var index = 0; index < stops.length; index++) ...[
                  _ItineraryStopRow(
                    stop: stops[index],
                    order: index + 1,
                    canMoveUp: index > 0,
                    canMoveDown: index < stops.length - 1,
                    onMoveUp:
                        onMove == null ? null : () => onMove!(index, index - 1),
                    onMoveDown:
                        onMove == null ? null : () => onMove!(index, index + 1),
                    onEditTime: onEditTime == null
                        ? null
                        : () => onEditTime!(stops[index]),
                    onDelete:
                        onDelete == null ? null : () => onDelete!(stops[index]),
                  ),
                  if (index < stops.length - 1)
                    _MovementRow(nextStop: stops[index + 1]),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.md),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            key: const ValueKey('confirm-route-button'),
            onPressed: stops.isEmpty ? null : onConfirm,
            icon: const Icon(Icons.check_rounded),
            label: const Text('이 일정으로 확정하기'),
          ),
        ),
      ],
    );
  }
}

class _ItinerarySummary extends StatelessWidget {
  const _ItinerarySummary({required this.stops});

  final List<PlanItineraryStop> stops;

  @override
  Widget build(BuildContext context) {
    final travelMinutes =
        _sumNumbers(stops.map((stop) => stop.place.transport));
    final expectedCost = _formatExpectedCost(stops);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: ChiwawaSpacing.sm,
        vertical: ChiwawaSpacing.sm,
      ),
      decoration: const BoxDecoration(
        color: ChiwawaColors.surfaceMuted,
        border: Border(
          top: BorderSide(color: ChiwawaColors.border),
          bottom: BorderSide(color: ChiwawaColors.border),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: _SummaryItem(
              key: const ValueKey('itinerary-summary-places'),
              icon: Icons.place_outlined,
              label: '방문 장소',
              value: '${stops.length}곳',
            ),
          ),
          const _SummaryDivider(),
          Expanded(
            child: _SummaryItem(
              key: const ValueKey('itinerary-summary-travel-time'),
              icon: Icons.directions_walk_rounded,
              label: '이동 시간',
              value: travelMinutes == 0 ? '확인 필요' : '약 $travelMinutes분',
            ),
          ),
          const _SummaryDivider(),
          Expanded(
            child: _SummaryItem(
              key: const ValueKey('itinerary-summary-cost'),
              icon: Icons.payments_outlined,
              label: '예상 비용',
              value: expectedCost,
            ),
          ),
        ],
      ),
    );
  }

  int _sumNumbers(Iterable<String> values) {
    return values.fold<int>(0, (sum, value) {
      final match = RegExp(r'(\d+)\s*분').firstMatch(value);
      return sum + (int.tryParse(match?.group(1) ?? '') ?? 0);
    });
  }

  String _formatExpectedCost(List<PlanItineraryStop> stops) {
    final costs = stops
        .map((stop) => stop.place.travelCost.trim())
        .where((cost) => cost.isNotEmpty && cost != '무료')
        .toList(growable: false);
    if (costs.isEmpty) return '무료';

    final symbol = RegExp(r'[^\d\s,.]').firstMatch(costs.first)?.group(0) ?? '';
    final amount = costs.fold<int>(0, (sum, cost) {
      final digits = cost.replaceAll(RegExp(r'[^\d]'), '');
      return sum + (int.tryParse(digits) ?? 0);
    });
    return amount == 0 ? '확인 필요' : '$symbol$amount';
  }
}

class _SummaryItem extends StatelessWidget {
  const _SummaryItem({
    required this.icon,
    required this.label,
    required this.value,
    super.key,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18, color: ChiwawaColors.primary),
        const SizedBox(height: ChiwawaSpacing.xxs),
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: ChiwawaColors.textPrimary,
            fontSize: 13,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: ChiwawaColors.textSecondary,
            fontSize: 10,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _SummaryDivider extends StatelessWidget {
  const _SummaryDivider();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: 40,
      color: ChiwawaColors.border,
    );
  }
}

enum _StopAction { moveUp, moveDown, editTime, delete }

class _ItineraryStopRow extends StatelessWidget {
  const _ItineraryStopRow({
    required this.stop,
    required this.order,
    required this.canMoveUp,
    required this.canMoveDown,
    required this.onMoveUp,
    required this.onMoveDown,
    required this.onEditTime,
    required this.onDelete,
  });

  final PlanItineraryStop stop;
  final int order;
  final bool canMoveUp;
  final bool canMoveDown;
  final VoidCallback? onMoveUp;
  final VoidCallback? onMoveDown;
  final VoidCallback? onEditTime;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      key: ValueKey('itinerary-stop-${stop.id}'),
      constraints: const BoxConstraints(minHeight: 72),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 6, 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 52,
              child: TextButton(
                key: ValueKey('itinerary-time-${stop.id}'),
                style: TextButton.styleFrom(
                  minimumSize: const Size(52, 44),
                  padding: EdgeInsets.zero,
                  foregroundColor: ChiwawaColors.textPrimary,
                ),
                onPressed: onEditTime,
                child: Text(
                  stop.startTime,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),
            const SizedBox(width: ChiwawaSpacing.sm),
            Container(
              width: 26,
              height: 26,
              margin: const EdgeInsets.only(top: 9),
              alignment: Alignment.center,
              decoration: const BoxDecoration(
                color: ChiwawaColors.primary,
                shape: BoxShape.circle,
              ),
              child: Text(
                '$order',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            const SizedBox(width: ChiwawaSpacing.sm),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(top: 5),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      stop.place.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: ChiwawaSpacing.xxs),
                    Text(
                      '${stop.place.category} · 체류 ${stop.place.duration}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: ChiwawaColors.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
            ),
            PopupMenuButton<_StopAction>(
              tooltip: '일정 편집',
              icon: const Icon(Icons.more_vert_rounded),
              onSelected: (action) {
                switch (action) {
                  case _StopAction.moveUp:
                    onMoveUp?.call();
                  case _StopAction.moveDown:
                    onMoveDown?.call();
                  case _StopAction.editTime:
                    onEditTime?.call();
                  case _StopAction.delete:
                    onDelete?.call();
                }
              },
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: _StopAction.moveUp,
                  enabled: canMoveUp && onMoveUp != null,
                  child: const _MenuLabel(
                    icon: Icons.arrow_upward_rounded,
                    label: '위로 이동',
                  ),
                ),
                PopupMenuItem(
                  value: _StopAction.moveDown,
                  enabled: canMoveDown && onMoveDown != null,
                  child: const _MenuLabel(
                    icon: Icons.arrow_downward_rounded,
                    label: '아래로 이동',
                  ),
                ),
                PopupMenuItem(
                  value: _StopAction.editTime,
                  enabled: onEditTime != null,
                  child: const _MenuLabel(
                    icon: Icons.schedule_rounded,
                    label: '시간 수정',
                  ),
                ),
                PopupMenuItem(
                  value: _StopAction.delete,
                  enabled: onDelete != null,
                  child: const _MenuLabel(
                    icon: Icons.delete_outline_rounded,
                    label: '일정에서 삭제',
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MovementRow extends StatelessWidget {
  const _MovementRow({required this.nextStop});

  final PlanItineraryStop nextStop;

  @override
  Widget build(BuildContext context) {
    final walk = nextStop.place.transport.contains('도보');
    final cost = nextStop.place.travelCost.trim();
    return Container(
      height: 42,
      margin: const EdgeInsets.only(left: 76, right: 12),
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: const BoxDecoration(
        color: ChiwawaColors.movementSurface,
        borderRadius: BorderRadius.all(
          Radius.circular(ChiwawaRadii.control),
        ),
      ),
      child: Row(
        children: [
          Icon(
            walk ? Icons.directions_walk_rounded : Icons.train_rounded,
            size: 17,
            color: ChiwawaColors.movement,
          ),
          const SizedBox(width: ChiwawaSpacing.xs),
          Expanded(
            child: Text(
              nextStop.place.transport,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: ChiwawaColors.movement,
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          if (cost.isNotEmpty)
            Text(
              cost,
              style: const TextStyle(
                color: ChiwawaColors.movement,
                fontSize: 12,
                fontWeight: FontWeight.w900,
              ),
            ),
        ],
      ),
    );
  }
}

class _MenuLabel extends StatelessWidget {
  const _MenuLabel({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 19),
        const SizedBox(width: ChiwawaSpacing.sm),
        Text(label),
      ],
    );
  }
}
