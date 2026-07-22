import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../models/plan_itinerary.dart';
import 'plan_itinerary_workspace.dart';

class RouteOptimizationSection extends StatelessWidget {
  const RouteOptimizationSection({
    required this.state,
    required this.canOptimize,
    required this.onOptimize,
    required this.onConfirm,
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
        if (state.status == AiJobStatus.done ||
            (itinerary?.isNotEmpty ?? false)) ...[
          const SizedBox(height: 22),
          PlanItineraryWorkspace(
            stops: itinerary ?? _stopsFrom(state.places),
            onMove: onMove,
            onEditTime: onEditTime,
            onDelete: onDelete,
            onConfirm: onConfirm,
          ),
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
        borderRadius: BorderRadius.circular(16),
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
