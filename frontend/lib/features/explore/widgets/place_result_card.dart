import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';

class PlaceResultCard extends StatelessWidget {
  const PlaceResultCard({
    required this.result,
    required this.imagePath,
    required this.isSaved,
    required this.onEdit,
    required this.onDirections,
    required this.onAddToPlan,
    super.key,
  });

  final PhotoSearchResult result;
  final String? imagePath;
  final bool isSaved;
  final VoidCallback onEdit;
  final VoidCallback onDirections;
  final VoidCallback onAddToPlan;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
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
                  child: imagePath == null
                      ? const _PlaceImagePlaceholder()
                      : kIsWeb
                          ? Image.network(
                              imagePath!,
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) =>
                                  const _PlaceImagePlaceholder(),
                            )
                          : Image.file(
                              File(imagePath!),
                              fit: BoxFit.cover,
                              errorBuilder: (context, error, stackTrace) =>
                                  const _PlaceImagePlaceholder(),
                            ),
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
                              fontWeight: FontWeight.w700,
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
                    if (result.confidence != null) ...[
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Icon(
                            Icons.verified_rounded,
                            color: ChiwawaColors.success,
                            size: 16,
                          ),
                          const SizedBox(width: 5),
                          Text(
                            '사진 일치도 ${(result.confidence! * 100).round()}%',
                            style: Theme.of(context)
                                .textTheme
                                .bodySmall
                                ?.copyWith(color: ChiwawaColors.success),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_location_alt_rounded, size: 18),
                  label: const Text('장소 수정'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton.icon(
                  onPressed: onDirections,
                  icon: const Icon(Icons.navigation, size: 18),
                  label: const Text('길찾기'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onAddToPlan,
              icon: Icon(
                isSaved ? Icons.check_rounded : Icons.add_rounded,
                size: 18,
              ),
              label: const Text('일정에 추가'),
            ),
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
