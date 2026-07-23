import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../shared/widgets/app_section_header.dart';
import '../models/plan_day_constraint.dart';

class PlanDayConstraintSection extends StatefulWidget {
  const PlanDayConstraintSection({
    required this.day,
    required this.constraint,
    required this.onStartPlaceChanged,
    required this.onStartTimeChanged,
    required this.onEndPlaceChanged,
    required this.onEndTimeChanged,
    required this.onMaxPlaceCountChanged,
    super.key,
  });

  final int day;
  final PlanDayConstraint constraint;
  final ValueChanged<String> onStartPlaceChanged;
  final ValueChanged<String> onStartTimeChanged;
  final ValueChanged<String> onEndPlaceChanged;
  final ValueChanged<String> onEndTimeChanged;
  final ValueChanged<int> onMaxPlaceCountChanged;

  @override
  State<PlanDayConstraintSection> createState() =>
      _PlanDayConstraintSectionState();
}

class _PlanDayConstraintSectionState extends State<PlanDayConstraintSection> {
  late final TextEditingController _startPlaceController;
  late final TextEditingController _endPlaceController;

  @override
  void initState() {
    super.initState();
    _startPlaceController = TextEditingController(
      text: widget.constraint.startPlace,
    );
    _endPlaceController = TextEditingController(
      text: widget.constraint.endPlace,
    );
  }

  @override
  void didUpdateWidget(covariant PlanDayConstraintSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    _syncController(_startPlaceController, widget.constraint.startPlace);
    _syncController(_endPlaceController, widget.constraint.endPlace);
  }

  @override
  void dispose() {
    _startPlaceController.dispose();
    _endPlaceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final constraint = widget.constraint;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionHeader(
          title: '하루 시작과 마무리',
          description: '출발과 도착 시간을 정하면 무리 없는 동선을 만들 수 있어요.',
          trailing: Text(
            '${widget.day}일차',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: ChiwawaColors.primary,
                  fontWeight: FontWeight.w800,
                ),
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.md),
        _ConstraintPointRow(
          role: '출발',
          icon: Icons.trip_origin_rounded,
          placeController: _startPlaceController,
          placeKey: ValueKey('plan-start-place-${widget.day}'),
          timeKey: ValueKey('plan-start-time-${widget.day}'),
          time: constraint.startTime,
          onPlaceChanged: widget.onStartPlaceChanged,
          onTimePressed: () => _pickTime(
            context,
            initialValue: constraint.startTime,
            helpText: '출발 시간 선택',
            onChanged: widget.onStartTimeChanged,
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
        _ConstraintPointRow(
          role: '도착',
          icon: Icons.location_on_rounded,
          placeController: _endPlaceController,
          placeKey: ValueKey('plan-end-place-${widget.day}'),
          timeKey: ValueKey('plan-end-time-${widget.day}'),
          time: constraint.endTime,
          onPlaceChanged: widget.onEndPlaceChanged,
          onTimePressed: () => _pickTime(
            context,
            initialValue: constraint.endTime,
            helpText: '도착 시간 선택',
            onChanged: widget.onEndTimeChanged,
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        _PlaceCountControl(
          day: widget.day,
          value: constraint.maxPlaceCount,
          onChanged: widget.onMaxPlaceCountChanged,
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

  void _syncController(TextEditingController controller, String value) {
    if (controller.text == value) return;
    controller.value = controller.value.copyWith(
      text: value,
      selection: TextSelection.collapsed(offset: value.length),
      composing: TextRange.empty,
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

class _ConstraintPointRow extends StatelessWidget {
  const _ConstraintPointRow({
    required this.role,
    required this.icon,
    required this.placeController,
    required this.placeKey,
    required this.timeKey,
    required this.time,
    required this.onPlaceChanged,
    required this.onTimePressed,
  });

  final String role;
  final IconData icon;
  final TextEditingController placeController;
  final Key placeKey;
  final Key timeKey;
  final String time;
  final ValueChanged<String> onPlaceChanged;
  final VoidCallback onTimePressed;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: const BoxDecoration(
            color: ChiwawaColors.secondary,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 17, color: ChiwawaColors.primary),
        ),
        const SizedBox(width: ChiwawaSpacing.sm),
        Expanded(
          child: TextFormField(
            key: placeKey,
            controller: placeController,
            onChanged: onPlaceChanged,
            textInputAction: TextInputAction.done,
            maxLines: 1,
            decoration: InputDecoration(
              labelText: '$role 장소',
              hintText: '$role 장소를 입력하세요',
            ),
          ),
        ),
        const SizedBox(width: ChiwawaSpacing.xs),
        SizedBox(
          width: 88,
          height: ChiwawaControlSizes.minimumInteractive,
          child: OutlinedButton(
            key: timeKey,
            onPressed: onTimePressed,
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              foregroundColor: ChiwawaColors.primary,
              side: const BorderSide(color: ChiwawaColors.border),
            ),
            child: Text(
              time,
              maxLines: 1,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
        ),
      ],
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
