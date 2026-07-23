import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../app/theme.dart';
import '../../../core/models/memorial_models.dart';
import '../../../shared/widgets/app_viewport.dart';

Future<void> showMemorialShareSheet(
  BuildContext context, {
  required MemorialOverview? overview,
  required DateTime date,
  required MemorialDayTimeline? timeline,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    constraints: const BoxConstraints(maxWidth: AppLayout.maxContentWidth),
    backgroundColor: Colors.transparent,
    builder: (_) => MemorialShareSheet(
      overview: overview,
      date: date,
      timeline: timeline,
    ),
  );
}

class MemorialShareSheet extends StatefulWidget {
  const MemorialShareSheet({
    required this.overview,
    required this.date,
    required this.timeline,
    super.key,
  });

  final MemorialOverview? overview;
  final DateTime date;
  final MemorialDayTimeline? timeline;

  @override
  State<MemorialShareSheet> createState() => _MemorialShareSheetState();
}

class _MemorialShareSheetState extends State<MemorialShareSheet> {
  bool _includeLocation = false;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      clipBehavior: Clip.antiAlias,
      borderRadius: const BorderRadius.vertical(
        top: Radius.circular(ChiwawaRadii.sheet),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: ChiwawaColors.textMuted,
                  borderRadius: BorderRadius.circular(ChiwawaRadii.round),
                ),
              ),
            ),
            Text('여행 기록 공유', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 6),
            Text(
              '공유할 내용에 사진 위치를 포함할지 선택해요.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: ChiwawaColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('위치 정보 포함'),
              subtitle: const Text('기본값은 포함하지 않음'),
              value: _includeLocation,
              onChanged: (value) => setState(() => _includeLocation = value),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _copyShareText,
                icon: const Icon(Icons.copy_rounded),
                label: const Text('공유 내용 복사'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _copyShareText() async {
    final timeline = widget.timeline;
    final title = widget.overview?.tripInfo.tripName ?? 'chiwawa 여행 기록';
    final dateLabel =
        '${widget.date.year}.${widget.date.month.toString().padLeft(2, '0')}.'
        '${widget.date.day.toString().padLeft(2, '0')}';
    final buffer = StringBuffer('$title\n$dateLabel');
    if (timeline != null) {
      buffer.write('\n사진 ${timeline.photoCount}장');
      if (_includeLocation) {
        final places = timeline.items
            .map((entry) => entry.photo.address?.trim())
            .whereType<String>()
            .where((place) => place.isNotEmpty)
            .toSet();
        if (places.isNotEmpty) buffer.write('\n${places.join(' · ')}');
      }
    }
    await Clipboard.setData(ClipboardData(text: buffer.toString()));
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    Navigator.pop(context);
    messenger.showSnackBar(
      const SnackBar(content: Text('공유할 여행 기록을 복사했어요.')),
    );
  }
}
