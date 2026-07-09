import 'dart:io';

import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';

class PlaceResultCard extends StatelessWidget {
  const PlaceResultCard({
    required this.result,
    required this.imageFile,
    required this.isSaved,
    required this.onAddToPlan,
    super.key,
  });

  final PhotoSearchResult result;
  final File? imageFile;
  final bool isSaved;
  final VoidCallback onAddToPlan;

  @override
  Widget build(BuildContext context) {
    return Container(
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
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  width: 80,
                  height: 80,
                  child: imageFile == null
                      ? const _PlaceImagePlaceholder()
                      : Image.file(imageFile!, fit: BoxFit.cover),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (isSaved) ...[
                      const _SavedBadge(),
                      const SizedBox(height: 8),
                    ],
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            result.name,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 16,
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
                            color: ChiwawaColors.secondary,
                            borderRadius: BorderRadius.circular(99),
                          ),
                          child: Text(
                            result.category,
                            style: const TextStyle(
                              color: ChiwawaColors.primary,
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      result.address,
                      style: const TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            height: 120,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: ChiwawaColors.background,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: ChiwawaColors.border),
            ),
            child: const Text(
              '지도',
              style: TextStyle(
                color: ChiwawaColors.textMuted,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.navigation, size: 18),
                  label: const Text('경로 안내'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onAddToPlan,
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('일정에 추가'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SavedBadge extends StatelessWidget {
  const _SavedBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: ChiwawaColors.secondary,
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.check_circle_rounded,
            size: 14,
            color: ChiwawaColors.primary,
          ),
          SizedBox(width: 4),
          Text(
            '일정 후보 저장됨',
            style: TextStyle(
              color: ChiwawaColors.primary,
              fontSize: 11,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlaceImagePlaceholder extends StatelessWidget {
  const _PlaceImagePlaceholder();

  @override
  Widget build(BuildContext context) {
    return const DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFFFD7DF), Color(0xFFFFF1C7)],
        ),
      ),
      child: Icon(
        Icons.landscape_rounded,
        color: ChiwawaColors.primary,
        size: 34,
      ),
    );
  }
}
