import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/mock_data.dart';

class DailySection extends StatelessWidget {
  const DailySection({
    required this.day,
    required this.seedOffset,
    super.key,
  });

  final MemorialDay day;
  final int seedOffset;

  @override
  Widget build(BuildContext context) {
    final visiblePhotos = day.photos.clamp(3, 6).toInt();

    return Container(
      padding: const EdgeInsets.all(16),
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
                  day.date,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              Text(
                '사진 ${day.photos}장',
                style: const TextStyle(
                  color: ChiwawaColors.textSecondary,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final place in day.places)
                Chip(
                  label: Text(place),
                  backgroundColor: ChiwawaColors.secondary,
                  labelStyle: const TextStyle(
                    color: ChiwawaColors.primary,
                    fontWeight: FontWeight.w700,
                  ),
                  side: BorderSide.none,
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
          const SizedBox(height: 12),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
            ),
            itemCount: visiblePhotos,
            itemBuilder: (context, index) {
              return ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(
                  'https://picsum.photos/200/200?random=${seedOffset + index + 30}',
                  fit: BoxFit.cover,
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
