import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';

class TripSummaryCard extends StatelessWidget {
  const TripSummaryCard({
    required this.tripInfo,
    required this.summary,
    super.key,
  });

  final TripInfo tripInfo;
  final MemorialSummary summary;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            tripInfo.tripName,
            style: const TextStyle(
              color: ChiwawaColors.textPrimary,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            tripInfo.period,
            style: const TextStyle(color: ChiwawaColors.textSecondary),
          ),
          const SizedBox(height: ChiwawaSpacing.md),
          const Divider(height: 1),
          const SizedBox(height: ChiwawaSpacing.md),
          Row(
            children: [
              _SummaryMetric(label: '총', value: '${summary.days}일'),
              _SummaryMetric(label: '방문', value: '${summary.places}곳'),
              _SummaryMetric(label: '이동', value: summary.distance),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryMetric extends StatelessWidget {
  const _SummaryMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              color: ChiwawaColors.primary,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
