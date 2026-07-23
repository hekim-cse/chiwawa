import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/transport_mode.dart';
import '../../../shared/widgets/adaptive_segmented_control.dart';
import '../../../shared/widgets/app_section_header.dart';

class PlanTransportModeSection extends StatelessWidget {
  const PlanTransportModeSection({
    required this.selected,
    required this.onSelected,
    super.key,
  });

  final TransportMode selected;
  final ValueChanged<TransportMode> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionHeader(
          title: '이동수단',
          description: '이동 방법에 따라 방문 순서와 예상 시간이 달라져요.',
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        AdaptiveSegmentedControl<TransportMode>(
          segments: [
            for (final mode in TransportMode.values)
              AdaptiveSegment(
                key: ValueKey('plan-transport-${mode.backendCode}'),
                value: mode,
                label: mode.label,
              ),
          ],
          selected: selected,
          onSelected: onSelected,
        ),
        const SizedBox(height: ChiwawaSpacing.xs),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 180),
          child: Row(
            key: ValueKey(selected),
            children: [
              Icon(
                _iconFor(selected),
                size: 17,
                color: ChiwawaColors.primary,
              ),
              const SizedBox(width: ChiwawaSpacing.xs),
              Expanded(
                child: Text(
                  '${selected.label} 기준으로 방문 순서와 이동 시간을 계산해요.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: ChiwawaColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

IconData _iconFor(TransportMode mode) {
  return switch (mode) {
    TransportMode.walk => Icons.directions_walk_rounded,
    TransportMode.drive => Icons.directions_car_filled_rounded,
    TransportMode.transit => Icons.train_rounded,
  };
}
