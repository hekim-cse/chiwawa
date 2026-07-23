import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../../../shared/widgets/adaptive_segmented_control.dart';

class TravelPreferenceSection extends StatelessWidget {
  const TravelPreferenceSection({
    required this.preference,
    required this.onThemeChanged,
    required this.onPaceChanged,
    super.key,
  });

  final TravelPreference preference;
  final void Function(TravelTheme theme, bool selected) onThemeChanged;
  final ValueChanged<TravelPace> onPaceChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '추가 추천 조건',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 6),
        const Text(
          '장소를 정한 뒤 취향과 일정 속도를 추가로 알려 주세요.',
          style: TextStyle(
            color: ChiwawaColors.textSecondary,
            fontSize: 12,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final theme in TravelTheme.values)
              FilterChip(
                key: ValueKey('plan-theme-${theme.code}'),
                label: Text(theme.label),
                selected: preference.themes.contains(theme),
                onSelected: (selected) => onThemeChanged(theme, selected),
                selectedColor: ChiwawaColors.primary,
                checkmarkColor: Colors.white,
                labelStyle: TextStyle(
                  color: preference.themes.contains(theme)
                      ? Colors.white
                      : ChiwawaColors.textSecondary,
                  fontWeight: preference.themes.contains(theme)
                      ? FontWeight.w700
                      : FontWeight.w600,
                ),
                side: const BorderSide(color: ChiwawaColors.border),
              ),
          ],
        ),
        const SizedBox(height: 14),
        AdaptiveSegmentedControl<TravelPace>(
          segments: [
            for (final pace in TravelPace.values)
              AdaptiveSegment(value: pace, label: pace.label),
          ],
          selected: preference.pace,
          onSelected: onPaceChanged,
        ),
      ],
    );
  }
}
