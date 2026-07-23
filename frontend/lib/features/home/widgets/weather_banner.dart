import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../../../core/providers/data_providers.dart';
import '../../../shared/widgets/async_value_view.dart';

class WeatherBanner extends ConsumerWidget {
  const WeatherBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AsyncValueView<TripInfo>(
      value: ref.watch(tripInfoProvider),
      loadingHeight: 76,
      onRetry: () => ref.invalidate(tripInfoProvider),
      builder: (tripInfo) => _banner(tripInfo),
    );
  }

  Widget _banner(TripInfo tripInfo) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ChiwawaColors.secondary,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Row(
        children: [
          const Icon(Icons.wb_sunny, color: ChiwawaColors.primary, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${tripInfo.city.split(',').first} ${tripInfo.weather}',
                  style: const TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  '오늘 일정 잘 될 것 같아요',
                  style: TextStyle(
                    color: ChiwawaColors.textSecondary,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
