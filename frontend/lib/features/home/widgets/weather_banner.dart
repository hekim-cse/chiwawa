import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/mock_data.dart';

class WeatherBanner extends StatelessWidget {
  const WeatherBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ChiwawaColors.secondary,
        borderRadius: BorderRadius.circular(12),
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
