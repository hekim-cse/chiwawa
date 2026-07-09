import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';

class RouteResultCard extends StatelessWidget {
  const RouteResultCard({
    required this.place,
    required this.order,
    required this.isLast,
    super.key,
  });

  final RoutePlace place;
  final int order;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 38,
          child: Column(
            children: [
              CircleAvatar(
                radius: 15,
                backgroundColor: ChiwawaColors.primary,
                child: Text(
                  '$order',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              if (!isLast)
                Container(
                  width: 2,
                  height: 64,
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  color: ChiwawaColors.border,
                ),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: ChiwawaColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        place.name,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: ChiwawaColors.background,
                        borderRadius: BorderRadius.circular(99),
                      ),
                      child: Text(
                        place.category,
                        style: const TextStyle(
                          color: ChiwawaColors.textSecondary,
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    const Icon(
                      Icons.directions_transit,
                      size: 16,
                      color: ChiwawaColors.textMuted,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        '이전 장소에서 ${place.transport}',
                        style: const TextStyle(
                          color: ChiwawaColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(
                      Icons.schedule,
                      size: 16,
                      color: ChiwawaColors.textMuted,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '예상 관람 ${place.duration}',
                      style: const TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
