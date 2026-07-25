import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/route_planning_models.dart';
import '../../../core/models/transport_mode.dart';
import '../../../core/models/travel_models.dart';
import '../models/plan_itinerary.dart';
import 'plan_itinerary_workspace.dart';
import 'plan_recommendations_section.dart';

class RouteOptimizationSection extends StatelessWidget {
  const RouteOptimizationSection({
    required this.state,
    required this.canOptimize,
    required this.onOptimize,
    required this.onConfirm,
    this.onAddRecommendation,
    this.transportMode = TransportMode.transit,
    this.itinerary,
    this.onMove,
    this.onEditTime,
    this.onDelete,
    super.key,
  });

  final RouteOptimizationState state;
  final bool canOptimize;
  final VoidCallback onOptimize;
  final VoidCallback onConfirm;
  final Future<bool> Function(RouteRecommendation recommendation)?
      onAddRecommendation;
  final TransportMode transportMode;
  final List<PlanItineraryStop>? itinerary;
  final void Function(int fromIndex, int toIndex)? onMove;
  final ValueChanged<PlanItineraryStop>? onEditTime;
  final ValueChanged<PlanItineraryStop>? onDelete;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            key: const ValueKey('plan-optimize-route'),
            onPressed: state.isWorking || !canOptimize ? null : onOptimize,
            icon: state.isWorking
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.4,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.auto_awesome),
            label: Text(state.isWorking ? '최적 경로 계산 중' : 'AI 경로 최적화'),
          ),
        ),
        if (state.status == AiJobStatus.failed) ...[
          const SizedBox(height: 16),
          _RouteFailureCard(
            message: state.message ?? '경로 최적화에 실패했어요.',
            onRetry: onOptimize,
          ),
        ],
        if (state.status == AiJobStatus.done &&
            state.result?.isAvailable == false) ...[
          const SizedBox(height: ChiwawaSpacing.md),
          _RouteUnavailableCard(result: state.result!),
        ],
        if ((state.status == AiJobStatus.done &&
                state.result?.isAvailable != false) ||
            (itinerary?.isNotEmpty ?? false)) ...[
          const SizedBox(height: 22),
          PlanItineraryWorkspace(
            stops: itinerary ?? _stopsFrom(state.places),
            transportMode: transportMode,
            result: state.result,
            onMove: onMove,
            onEditTime: onEditTime,
            onDelete: onDelete,
            onConfirm: onConfirm,
          ),
          if ((state.result?.recommendationGroups.isNotEmpty ?? false) &&
              onAddRecommendation != null) ...[
            const SizedBox(height: ChiwawaSpacing.section),
            PlanRecommendationsSection(
              groups: state.result!.recommendationGroups,
              onAdd: onAddRecommendation!,
            ),
          ],
        ],
      ],
    );
  }

  List<PlanItineraryStop> _stopsFrom(List<RoutePlace> places) {
    return [
      for (var index = 0; index < places.length; index++)
        PlanItineraryStop(
          id: '${places[index].identityKey}-$index',
          startTime: '${(9 + index * 2).toString().padLeft(2, '0')}:00',
          place: places[index],
        ),
    ];
  }
}

class _RouteUnavailableCard extends StatelessWidget {
  const _RouteUnavailableCard({required this.result});

  final RouteOptimizationResult result;

  @override
  Widget build(BuildContext context) {
    final details = [
      ...result.warnings,
      for (final segment in result.missingSegments) '확인할 구간: $segment',
    ];
    return Container(
      key: const ValueKey('route-option-unavailable'),
      padding: const EdgeInsets.all(ChiwawaSpacing.sm),
      decoration: BoxDecoration(
        color: ChiwawaColors.secondary,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.route_outlined,
                color: ChiwawaColors.primary,
                size: 20,
              ),
              SizedBox(width: ChiwawaSpacing.xs),
              Expanded(
                child: Text(
                  '선택한 이동수단의 경로 정보가 부족해요',
                  style: TextStyle(
                    color: ChiwawaColors.primary,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: ChiwawaSpacing.xs),
          const Text(
            '다른 이동수단을 자동으로 고르지 않았어요. 위에서 직접 선택해 다시 계산해 주세요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
              height: 1.4,
            ),
          ),
          for (final detail in details) ...[
            const SizedBox(height: ChiwawaSpacing.xxs),
            Text(
              '• $detail',
              style: const TextStyle(
                color: ChiwawaColors.textSecondary,
                fontSize: 12,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _RouteFailureCard extends StatelessWidget {
  const _RouteFailureCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.error_outline_rounded,
            color: ChiwawaColors.primary,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: ChiwawaColors.textSecondary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          TextButton(onPressed: onRetry, child: const Text('다시 시도')),
        ],
      ),
    );
  }
}
