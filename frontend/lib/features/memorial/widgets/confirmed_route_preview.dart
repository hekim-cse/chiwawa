import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';

class ConfirmedRoutePreview extends StatelessWidget {
  const ConfirmedRoutePreview({required this.places, super.key});

  final List<RoutePlace> places;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.route_rounded,
                color: ChiwawaColors.primary,
                size: 20,
              ),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  '확정 일정 미리보기',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'AI 일정 설계에서 확정한 동선을 기록 흐름으로 이어봤어요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 12),
          for (var index = 0; index < places.length; index++)
            _ConfirmedRouteRow(
              key: ValueKey(
                'confirmed-route-${places[index].identityKey}-$index',
              ),
              order: index + 1,
              place: places[index],
              isLast: index == places.length - 1,
            ),
        ],
      ),
    );
  }
}

class _ConfirmedRouteRow extends StatelessWidget {
  const _ConfirmedRouteRow({
    required this.order,
    required this.place,
    required this.isLast,
    super.key,
  });

  final int order;
  final RoutePlace place;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 28,
          child: Column(
            children: [
              CircleAvatar(
                radius: 12,
                backgroundColor: ChiwawaColors.secondary,
                child: Text(
                  '$order',
                  style: const TextStyle(
                    color: ChiwawaColors.primary,
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              if (!isLast)
                Container(
                  width: 1.4,
                  height: 28,
                  margin: const EdgeInsets.symmetric(vertical: 3),
                  color: ChiwawaColors.border,
                ),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Padding(
            padding: EdgeInsets.only(bottom: isLast ? 0 : 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  place.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 3),
                Text(
                  '${place.category} · ${place.duration}',
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
        ),
      ],
    );
  }
}
