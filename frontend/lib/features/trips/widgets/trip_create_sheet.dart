import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../../../shared/widgets/adaptive_segmented_control.dart';
import '../../../shared/widgets/app_viewport.dart';
import '../trip_controller.dart';
import 'trip_inline_error.dart';

Future<Trip?> showTripCreateSheet(BuildContext context) {
  return showModalBottomSheet<Trip>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    constraints: const BoxConstraints(maxWidth: AppLayout.maxContentWidth),
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(
        top: Radius.circular(ChiwawaRadii.sheet),
      ),
    ),
    builder: (_) => const TripCreateSheet(),
  );
}

class TripCreateSheet extends ConsumerStatefulWidget {
  const TripCreateSheet({super.key});

  @override
  ConsumerState<TripCreateSheet> createState() => _TripCreateSheetState();
}

class _TripCreateSheetState extends ConsumerState<TripCreateSheet> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _cityController = TextEditingController(text: '도쿄');
  late DateTimeRange _dateRange;
  int _travelers = 1;
  TravelPace _pace = TravelPace.balanced;
  final Set<TravelTheme> _themes = {
    TravelTheme.photoSpot,
    TravelTheme.culture,
  };

  @override
  void initState() {
    super.initState();
    final start = DateUtils.dateOnly(
      DateTime.now().add(const Duration(days: 30)),
    );
    _dateRange = DateTimeRange(
      start: start,
      end: start.add(const Duration(days: 3)),
    );
  }

  @override
  void dispose() {
    _titleController.dispose();
    _cityController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final catalog = ref.watch(tripCatalogProvider);
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(
          AppLayout.pageHorizontalPadding(context),
          12,
          AppLayout.pageHorizontalPadding(context),
          24,
        ),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: ChiwawaColors.textMuted,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      '새 여행 만들기',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: '닫기',
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextFormField(
                key: const ValueKey('trip-title-field'),
                controller: _titleController,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: '여행 이름',
                  hintText: '예: 도쿄 봄 여행',
                  prefixIcon: Icon(Icons.edit_rounded),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextFormField(
                key: const ValueKey('trip-city-field'),
                controller: _cityController,
                textInputAction: TextInputAction.done,
                decoration: const InputDecoration(
                  labelText: '도시',
                  prefixIcon: Icon(Icons.location_city_rounded),
                  border: OutlineInputBorder(),
                ),
                validator: (value) => value == null || value.trim().isEmpty
                    ? '도시를 입력해 주세요.'
                    : null,
              ),
              const SizedBox(height: 12),
              InkWell(
                key: const ValueKey('trip-date-range'),
                borderRadius: BorderRadius.circular(ChiwawaRadii.control),
                onTap: _pickDateRange,
                child: InputDecorator(
                  decoration: const InputDecoration(
                    labelText: '여행 날짜',
                    prefixIcon: Icon(Icons.date_range_rounded),
                    suffixIcon: Icon(Icons.chevron_right_rounded),
                    border: OutlineInputBorder(),
                  ),
                  child: Text(
                    '${DateFormat('yyyy.MM.dd').format(_dateRange.start)} - '
                    '${DateFormat('yyyy.MM.dd').format(_dateRange.end)}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              _FieldLabel(
                label: '여행 인원',
                trailing: _TravelerStepper(
                  value: _travelers,
                  onChanged: (value) => setState(() => _travelers = value),
                ),
              ),
              const SizedBox(height: 20),
              const _FieldLabel(label: '관심 테마'),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final theme in TravelTheme.values)
                    FilterChip(
                      key: ValueKey('trip-theme-${theme.code}'),
                      label: Text(theme.label),
                      selected: _themes.contains(theme),
                      onSelected: (selected) {
                        setState(() {
                          if (selected) {
                            _themes.add(theme);
                          } else {
                            _themes.remove(theme);
                          }
                        });
                      },
                    ),
                ],
              ),
              const SizedBox(height: 20),
              const _FieldLabel(label: '여행 스타일'),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: AdaptiveSegmentedControl<TravelPace>(
                  segments: [
                    for (final pace in TravelPace.values)
                      AdaptiveSegment(value: pace, label: pace.label),
                  ],
                  selected: _pace,
                  onSelected: (pace) => setState(() => _pace = pace),
                ),
              ),
              if (catalog.errorMessage != null) ...[
                const SizedBox(height: 14),
                TripInlineError(message: catalog.errorMessage!),
              ],
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  key: const ValueKey('submit-trip-create'),
                  onPressed: catalog.isCreating ? null : _submit,
                  icon: catalog.isCreating
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.check_rounded),
                  label: Text(catalog.isCreating ? '만드는 중' : '여행 만들기'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _pickDateRange() async {
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 3650)),
      initialDateRange: _dateRange,
      helpText: '여행 날짜 선택',
    );
    if (picked != null && mounted) setState(() => _dateRange = picked);
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final trip = await ref.read(tripCatalogProvider.notifier).createTrip(
          TripDraft(
            title: _titleController.text,
            city: _cityController.text.trim(),
            startDate: DateFormat('yyyy-MM-dd').format(_dateRange.start),
            endDate: DateFormat('yyyy-MM-dd').format(_dateRange.end),
            travelers: _travelers,
            interests: _themes.map((theme) => theme.code).toList(),
            travelStyle: _pace,
          ),
        );
    if (trip != null && mounted) Navigator.pop(context, trip);
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel({required this.label, this.trailing});

  final String label;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900),
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

class _TravelerStepper extends StatelessWidget {
  const _TravelerStepper({required this.value, required this.onChanged});

  final int value;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          key: const ValueKey('decrease-travelers'),
          tooltip: '인원 줄이기',
          visualDensity: VisualDensity.compact,
          onPressed: value > 1 ? () => onChanged(value - 1) : null,
          icon: const Icon(Icons.remove_circle_outline_rounded),
        ),
        SizedBox(
          width: 36,
          child: Text(
            '$value명',
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w900),
          ),
        ),
        IconButton(
          key: const ValueKey('increase-travelers'),
          tooltip: '인원 늘리기',
          visualDensity: VisualDensity.compact,
          onPressed: value < 20 ? () => onChanged(value + 1) : null,
          icon: const Icon(Icons.add_circle_outline_rounded),
        ),
      ],
    );
  }
}
