import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/route_planning_models.dart';
import '../../../shared/widgets/app_section_header.dart';

class PlanRecommendationsSection extends StatefulWidget {
  const PlanRecommendationsSection({
    required this.groups,
    required this.onAdd,
    super.key,
  });

  final List<RouteRecommendationGroup> groups;
  final Future<bool> Function(RouteRecommendation recommendation) onAdd;

  @override
  State<PlanRecommendationsSection> createState() =>
      _PlanRecommendationsSectionState();
}

class _PlanRecommendationsSectionState
    extends State<PlanRecommendationsSection> {
  String? _selectedCategory;
  RouteRecommendation? _selectedRecommendation;
  bool _isAdding = false;

  @override
  void didUpdateWidget(covariant PlanRecommendationsSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.groups.any((group) => group.category == _selectedCategory)) {
      _selectedCategory = null;
      _selectedRecommendation = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final availableGroups = widget.groups
        .where((group) => group.recommendations.isNotEmpty)
        .toList(growable: false);
    if (availableGroups.isEmpty) {
      return const _EmptyRecommendations();
    }
    final activeGroup = availableGroups.firstWhere(
      (group) => group.category == _selectedCategory,
      orElse: () => availableGroups.first,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionHeader(
          title: '경로 주변 추천',
          description: '원래 일정은 유지한 채, 넣어볼 장소와 시간 영향을 비교하세요.',
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        Wrap(
          spacing: ChiwawaSpacing.xs,
          runSpacing: ChiwawaSpacing.xs,
          children: [
            for (final group in availableGroups)
              ChoiceChip(
                key: ValueKey('recommendation-category-${group.category}'),
                label: Text(group.displayName),
                selected: group.category == activeGroup.category,
                onSelected: (_) {
                  setState(() {
                    _selectedCategory = group.category;
                    _selectedRecommendation = null;
                  });
                },
                selectedColor: ChiwawaColors.secondary,
                side: const BorderSide(color: ChiwawaColors.border),
                labelStyle: TextStyle(
                  color: group.category == activeGroup.category
                      ? ChiwawaColors.primary
                      : ChiwawaColors.textSecondary,
                  fontWeight: FontWeight.w800,
                ),
              ),
          ],
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        Material(
          color: Colors.transparent,
          child: Column(
            children: [
              for (var index = 0;
                  index < activeGroup.recommendations.length;
                  index++)
                _RecommendationRow(
                  recommendation: activeGroup.recommendations[index],
                  selected: identical(
                    activeGroup.recommendations[index],
                    _selectedRecommendation,
                  ),
                  showDivider: index != activeGroup.recommendations.length - 1,
                  onTap: () => setState(
                    () => _selectedRecommendation =
                        activeGroup.recommendations[index],
                  ),
                ),
            ],
          ),
        ),
        if (_selectedRecommendation != null) ...[
          const SizedBox(height: ChiwawaSpacing.sm),
          _RecommendationPreview(
            recommendation: _selectedRecommendation!,
            isAdding: _isAdding,
            onAdd: _addSelected,
          ),
        ],
      ],
    );
  }

  Future<void> _addSelected() async {
    final recommendation = _selectedRecommendation;
    if (recommendation == null || _isAdding) return;
    setState(() => _isAdding = true);
    try {
      await widget.onAdd(recommendation);
    } finally {
      if (mounted) setState(() => _isAdding = false);
    }
  }
}

class _RecommendationRow extends StatelessWidget {
  const _RecommendationRow({
    required this.recommendation,
    required this.selected,
    required this.showDivider,
    required this.onTap,
  });

  final RouteRecommendation recommendation;
  final bool selected;
  final bool showDivider;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final candidate = recommendation.candidate;
    final impact = recommendation.insertionImpact;
    return Semantics(
      container: true,
      explicitChildNodes: true,
      excludeSemantics: true,
      button: true,
      selected: selected,
      onTap: onTap,
      label:
          '${candidate.name}, ${candidate.formattedAddress}, ${impact.additionalMinutes}분 추가',
      child: InkWell(
        key: ValueKey('route-recommendation-${candidate.placeId}'),
        borderRadius: BorderRadius.circular(ChiwawaRadii.control),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: ChiwawaSpacing.sm,
            vertical: ChiwawaSpacing.sm,
          ),
          decoration: BoxDecoration(
            color: selected ? ChiwawaColors.secondary : Colors.transparent,
            border: showDivider
                ? const Border(
                    bottom: BorderSide(color: ChiwawaColors.border),
                  )
                : null,
          ),
          child: Row(
            children: [
              Icon(
                selected
                    ? Icons.check_circle_rounded
                    : Icons.add_location_alt_outlined,
                color: ChiwawaColors.primary,
                size: 21,
              ),
              const SizedBox(width: ChiwawaSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      candidate.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: ChiwawaColors.textPrimary,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: ChiwawaSpacing.xxs),
                    Text(
                      candidate.formattedAddress,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: ChiwawaSpacing.xs),
              Text(
                '+${impact.additionalMinutes}분',
                style: const TextStyle(
                  color: ChiwawaColors.primary,
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RecommendationPreview extends StatelessWidget {
  const _RecommendationPreview({
    required this.recommendation,
    required this.isAdding,
    required this.onAdd,
  });

  final RouteRecommendation recommendation;
  final bool isAdding;
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    final candidate = recommendation.candidate;
    final impact = recommendation.insertionImpact;
    final rating = candidate.rating;
    return Container(
      key: const ValueKey('route-recommendation-preview'),
      padding: const EdgeInsets.all(ChiwawaSpacing.sm),
      decoration: const BoxDecoration(
        color: ChiwawaColors.surfaceMuted,
        border: Border(
          top: BorderSide(color: ChiwawaColors.border),
          bottom: BorderSide(color: ChiwawaColors.border),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${candidate.name} 일정 영향',
            style: const TextStyle(
              color: ChiwawaColors.primary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: ChiwawaSpacing.xs),
          Wrap(
            spacing: ChiwawaSpacing.sm,
            runSpacing: ChiwawaSpacing.xs,
            children: [
              _ImpactLabel(
                icon: Icons.schedule_rounded,
                text:
                    '${impact.candidateArrivalTime}~${impact.candidateDepartureTime}',
              ),
              _ImpactLabel(
                icon: Icons.timelapse_rounded,
                text: '체류 ${impact.stayMinutes}분',
              ),
              _ImpactLabel(
                icon: Icons.flag_rounded,
                text: '종료 ${impact.updatedTimelineEndTime}',
              ),
              if (rating != null)
                _ImpactLabel(
                  icon: Icons.star_rounded,
                  text: candidate.userRatingCount == null
                      ? rating.toStringAsFixed(1)
                      : '${rating.toStringAsFixed(1)} · '
                          '${candidate.userRatingCount}개',
                ),
            ],
          ),
          const SizedBox(height: ChiwawaSpacing.sm),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              key: const ValueKey('add-route-recommendation'),
              onPressed: isAdding ? null : onAdd,
              icon: Icon(
                isAdding ? Icons.sync_rounded : Icons.add_rounded,
              ),
              label: Text(isAdding ? '일정 다시 계산 중' : '일정에 추가하고 재최적화'),
            ),
          ),
        ],
      ),
    );
  }
}

class _ImpactLabel extends StatelessWidget {
  const _ImpactLabel({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: ChiwawaColors.primary),
        const SizedBox(width: ChiwawaSpacing.xxs),
        Text(
          text,
          style: const TextStyle(
            color: ChiwawaColors.textSecondary,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _EmptyRecommendations extends StatelessWidget {
  const _EmptyRecommendations();

  @override
  Widget build(BuildContext context) {
    return const Text(
      '이 경로에 바로 넣을 수 있는 추천 장소가 아직 없어요.',
      style: TextStyle(
        color: ChiwawaColors.textSecondary,
        fontSize: 12,
      ),
    );
  }
}
