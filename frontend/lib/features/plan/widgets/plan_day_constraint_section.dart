import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/place_search_models.dart';
import '../../../shared/widgets/app_section_header.dart';
import '../models/plan_day_constraint.dart';
import '../plan_place_search_controller.dart';
import 'plan_place_search_field.dart';

class PlanDayConstraintSection extends StatelessWidget {
  const PlanDayConstraintSection({
    required this.day,
    required this.constraint,
    required this.startSearchState,
    required this.endSearchState,
    required this.onStartQueryChanged,
    required this.onStartPlaceSelected,
    required this.onStartRetry,
    required this.onStartTimeChanged,
    required this.onEndQueryChanged,
    required this.onEndPlaceSelected,
    required this.onEndRetry,
    required this.onEndTimeChanged,
    required this.onMaxPlaceCountChanged,
    super.key,
  });

  final int day;
  final PlanDayConstraint constraint;
  final PlanPlaceSearchState startSearchState;
  final PlanPlaceSearchState endSearchState;
  final ValueChanged<String> onStartQueryChanged;
  final ValueChanged<PlaceSearchCandidate> onStartPlaceSelected;
  final VoidCallback onStartRetry;
  final ValueChanged<String> onStartTimeChanged;
  final ValueChanged<String> onEndQueryChanged;
  final ValueChanged<PlaceSearchCandidate> onEndPlaceSelected;
  final VoidCallback onEndRetry;
  final ValueChanged<String> onEndTimeChanged;
  final ValueChanged<int> onMaxPlaceCountChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionHeader(
          title: '하루 시작과 마무리',
          description: '검색 결과에서 출발·도착 장소를 고르고 시간을 정해 주세요.',
          trailing: Text(
            '$day일차',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: ChiwawaColors.primary,
                  fontWeight: FontWeight.w800,
                ),
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.md),
        PlanPlaceSearchField(
          day: day,
          role: PlanPlaceRole.start,
          searchState: startSearchState,
          selectedPlace: constraint.startPlace,
          time: constraint.startTime,
          onQueryChanged: onStartQueryChanged,
          onPlaceSelected: onStartPlaceSelected,
          onRetry: onStartRetry,
          onTimePressed: () => _pickTime(
            context,
            initialValue: constraint.startTime,
            helpText: '출발 시간 선택',
            onChanged: onStartTimeChanged,
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(left: 15),
          child: Container(
            width: 2,
            height: 16,
            color: ChiwawaColors.secondary,
          ),
        ),
        PlanPlaceSearchField(
          day: day,
          role: PlanPlaceRole.end,
          searchState: endSearchState,
          selectedPlace: constraint.endPlace,
          time: constraint.endTime,
          onQueryChanged: onEndQueryChanged,
          onPlaceSelected: onEndPlaceSelected,
          onRetry: onEndRetry,
          onTimePressed: () => _pickTime(
            context,
            initialValue: constraint.endTime,
            helpText: '도착 시간 선택',
            onChanged: onEndTimeChanged,
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        _PlaceCountControl(
          day: day,
          value: constraint.maxPlaceCount,
          onChanged: onMaxPlaceCountChanged,
        ),
        AnimatedSize(
          duration: const Duration(milliseconds: 160),
          alignment: Alignment.topCenter,
          child: constraint.validationMessage == null
              ? const SizedBox.shrink()
              : Padding(
                  padding: const EdgeInsets.only(top: ChiwawaSpacing.xs),
                  child: Row(
                    key: const ValueKey('plan-day-constraint-error'),
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.info_outline_rounded,
                        size: 17,
                        color: ChiwawaColors.primaryPressed,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          constraint.validationMessage!,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: ChiwawaColors.primaryPressed,
                                    fontWeight: FontWeight.w700,
                                  ),
                        ),
                      ),
                    ],
                  ),
                ),
        ),
      ],
    );
  }

  Future<void> _pickTime(
    BuildContext context, {
    required String initialValue,
    required String helpText,
    required ValueChanged<String> onChanged,
  }) async {
    final parts = initialValue.split(':');
    final parsedHour = int.tryParse(parts.first);
    final parsedMinute = parts.length > 1 ? int.tryParse(parts[1]) : null;
    final initialTime = TimeOfDay(
      hour: parsedHour != null && parsedHour >= 0 && parsedHour < 24
          ? parsedHour
          : 9,
      minute: parsedMinute != null && parsedMinute >= 0 && parsedMinute < 60
          ? parsedMinute
          : 0,
    );
    final picked = await showTimePicker(
      context: context,
      initialTime: initialTime,
      helpText: helpText,
    );
    if (picked == null || !context.mounted) return;
    onChanged(
      '${picked.hour.toString().padLeft(2, '0')}:'
      '${picked.minute.toString().padLeft(2, '0')}',
    );
  }
}

class _PlaceCountControl extends StatelessWidget {
  const _PlaceCountControl({
    required this.day,
    required this.value,
    required this.onChanged,
  });

  final int day;
  final int value;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        const SizedBox(width: 44),
        Expanded(
          child: Text(
            '최대 방문 장소',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: ChiwawaColors.primary,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ),
        IconButton(
          key: ValueKey('plan-max-place-minus-$day'),
          onPressed: value > PlanDayConstraint.minimumPlaceCount
              ? () => onChanged(value - 1)
              : null,
          color: ChiwawaColors.primary,
          icon: const Icon(Icons.remove_circle_outline_rounded),
          tooltip: '최대 방문 장소 줄이기',
        ),
        SizedBox(
          width: 34,
          child: Text(
            '$value곳',
            key: ValueKey('plan-max-place-count-$day'),
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: ChiwawaColors.primary,
                  fontWeight: FontWeight.w800,
                ),
          ),
        ),
        IconButton(
          key: ValueKey('plan-max-place-plus-$day'),
          onPressed: value < PlanDayConstraint.maximumPlaceCount
              ? () => onChanged(value + 1)
              : null,
          color: ChiwawaColors.primary,
          icon: const Icon(Icons.add_circle_outline_rounded),
          tooltip: '최대 방문 장소 늘리기',
        ),
      ],
    );
  }
}
