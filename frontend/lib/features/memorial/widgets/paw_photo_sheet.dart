import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/memorial_map_models.dart';
import '../../../core/utils/time_formatters.dart';
import 'memorial_photo_image.dart';

class PawPhotoSheet extends StatelessWidget {
  const PawPhotoSheet({required this.cluster, super.key});

  final PawCluster cluster;

  @override
  Widget build(BuildContext context) {
    final time = formatTime(
      '${cluster.arrivalTime.hour}:${cluster.arrivalTime.minute}',
    );

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 42,
                height: 4,
                decoration: BoxDecoration(
                  color: ChiwawaColors.border,
                  borderRadius: BorderRadius.circular(ChiwawaRadii.round),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: Text(
                    cluster.placeName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: ChiwawaColors.textPrimary,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: ChiwawaColors.secondary,
                    borderRadius: BorderRadius.circular(ChiwawaRadii.round),
                  ),
                  child: Text(
                    '사진 ${cluster.photoCount}장',
                    style: const TextStyle(
                      color: ChiwawaColors.primary,
                      fontSize: 12,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              '$time 도착',
              style: const TextStyle(
                color: ChiwawaColors.textSecondary,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 116,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: cluster.photos.length,
                separatorBuilder: (_, __) => const SizedBox(width: 10),
                itemBuilder: (context, index) {
                  final photo = cluster.photos[index];
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(ChiwawaRadii.control),
                    child: MemorialPhotoImage(
                      assetPath: photo.assetPath,
                      fileUrl: photo.fileUrl,
                      width: 116,
                      height: 116,
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
