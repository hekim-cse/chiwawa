import 'package:flutter/material.dart';

import '../../app/theme.dart';

class AdaptiveSegment<T> {
  const AdaptiveSegment({
    required this.value,
    required this.label,
    this.key,
  });

  final T value;
  final String label;
  final Key? key;
}

class AdaptiveSegmentedControl<T> extends StatelessWidget {
  const AdaptiveSegmentedControl({
    required this.segments,
    required this.selected,
    required this.onSelected,
    super.key,
  });

  final List<AdaptiveSegment<T>> segments;
  final T selected;
  final ValueChanged<T> onSelected;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: ChiwawaControlSizes.minimumInteractive,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(ChiwawaRadii.control),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Row(
        children: [
          for (var index = 0; index < segments.length; index++) ...[
            Expanded(
              child: _SegmentButton<T>(
                key: segments[index].key,
                segment: segments[index],
                selected: segments[index].value == selected,
                onTap: () => onSelected(segments[index].value),
              ),
            ),
            if (index != segments.length - 1)
              const VerticalDivider(
                width: 1,
                thickness: 1,
                color: ChiwawaColors.border,
              ),
          ],
        ],
      ),
    );
  }
}

class _SegmentButton<T> extends StatelessWidget {
  const _SegmentButton({
    required this.segment,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final AdaptiveSegment<T> segment;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: segment.label,
      excludeSemantics: true,
      child: Material(
        color: selected ? ChiwawaColors.secondary : Colors.transparent,
        child: InkWell(
          onTap: onTap,
          overlayColor: WidgetStateProperty.resolveWith(
            ChiwawaTheme.primaryStateLayer,
          ),
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  segment.label,
                  maxLines: 1,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: selected
                            ? ChiwawaColors.primary
                            : ChiwawaColors.textPrimary,
                      ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
