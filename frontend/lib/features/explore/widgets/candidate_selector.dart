import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../../../shared/widgets/app_list_group.dart';
import '../../../shared/widgets/app_section_header.dart';

class CandidateSelector extends StatelessWidget {
  const CandidateSelector({
    required this.candidates,
    required this.selected,
    required this.onSelected,
    super.key,
  });

  final List<PhotoSearchResult> candidates;
  final PhotoSearchResult selected;
  final ValueChanged<PhotoSearchResult> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionHeader(
          title: '분석 후보',
          description: '가장 가까운 장소를 직접 선택해 주세요.',
          trailing: Text(
            '${candidates.length}곳',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: ChiwawaColors.textSecondary,
                ),
          ),
        ),
        const SizedBox(height: 8),
        AppListGroup(
          children: [
            for (var index = 0; index < candidates.length; index++)
              AppListRow(
                key: ValueKey(
                  'photo-candidate-${candidates[index].identityKey}',
                ),
                title: candidates[index].name,
                subtitle: [
                  candidates[index].category,
                  candidates[index].address,
                ].where((value) => value.trim().isNotEmpty).join(' · '),
                leading: Icon(
                  candidates[index].hasSameIdentityAs(selected)
                      ? Icons.radio_button_checked_rounded
                      : Icons.radio_button_unchecked_rounded,
                  color: candidates[index].hasSameIdentityAs(selected)
                      ? ChiwawaColors.primary
                      : ChiwawaColors.textMuted,
                ),
                trailing: _ConfidenceLabel(
                  confidence: candidates[index].confidence,
                  selected: candidates[index].hasSameIdentityAs(selected),
                ),
                showDivider: index != candidates.length - 1,
                onTap: () => onSelected(candidates[index]),
              ),
          ],
        ),
      ],
    );
  }
}

class _ConfidenceLabel extends StatelessWidget {
  const _ConfidenceLabel({required this.confidence, required this.selected});

  final double? confidence;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: selected ? ChiwawaColors.secondary : ChiwawaColors.surfaceMuted,
        borderRadius: BorderRadius.circular(ChiwawaRadii.round),
      ),
      child: Text(
        '${((confidence ?? 0) * 100).round()}%',
        style: TextStyle(
          color: selected ? ChiwawaColors.primary : ChiwawaColors.textSecondary,
          fontSize: 12,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}
