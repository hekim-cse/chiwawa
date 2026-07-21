import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/memorial_models.dart';
import '../../../core/utils/time_formatters.dart';
import '../../../shared/widgets/app_section_header.dart';
import 'memorial_photo_image.dart';

class MemorialDayPhotoSection extends StatelessWidget {
  const MemorialDayPhotoSection({
    required this.timeline,
    required this.onEditLocation,
    required this.onExclude,
    super.key,
  });

  final MemorialDayTimeline timeline;
  final ValueChanged<MemorialPhoto> onEditLocation;
  final ValueChanged<MemorialPhoto> onExclude;

  @override
  Widget build(BuildContext context) {
    if (timeline.items.isEmpty) {
      return const _EmptyDayPhotos();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppSectionHeader(
          title: '이날의 사진',
          trailing: Text(
            '${timeline.photoCount}장',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: ChiwawaColors.textSecondary,
                ),
          ),
        ),
        if (timeline.unlocatedPhotoCount > 0) ...[
          const SizedBox(height: 6),
          Text(
            '위치 없는 사진 ${timeline.unlocatedPhotoCount}장은 목록에만 보여요.',
            style: const TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
              height: 1.35,
            ),
          ),
        ],
        const SizedBox(height: ChiwawaSpacing.sm),
        SizedBox(
          height: 154,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: timeline.items.length,
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemBuilder: (context, index) {
              return _TimelinePhoto(
                entry: timeline.items[index],
                onEditLocation: () =>
                    onEditLocation(timeline.items[index].photo),
                onExclude: () => onExclude(timeline.items[index].photo),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _TimelinePhoto extends StatelessWidget {
  const _TimelinePhoto({
    required this.entry,
    required this.onEditLocation,
    required this.onExclude,
  });

  final MemorialTimelineEntry entry;
  final VoidCallback onEditLocation;
  final VoidCallback onExclude;

  @override
  Widget build(BuildContext context) {
    final photo = entry.photo;
    final time = formatTime('${photo.takenAt.hour}:${photo.takenAt.minute}');
    return SizedBox(
      width: 118,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: Stack(
              children: [
                MemorialPhotoImage(
                  assetPath: photo.assetPath,
                  fileUrl: photo.fileUrl,
                  width: 118,
                  height: 112,
                ),
                Positioned(
                  top: 4,
                  right: 4,
                  child: Material(
                    color: Colors.white.withValues(alpha: 0.92),
                    shape: const CircleBorder(),
                    child: SizedBox.square(
                      dimension: 40,
                      child: PopupMenuButton<_PhotoAction>(
                        key: ValueKey('memorial-photo-menu-${photo.id}'),
                        tooltip: '사진 편집',
                        icon: const Icon(Icons.more_horiz_rounded, size: 19),
                        iconSize: 19,
                        padding: EdgeInsets.zero,
                        onSelected: (action) {
                          switch (action) {
                            case _PhotoAction.editLocation:
                              onEditLocation();
                            case _PhotoAction.exclude:
                              onExclude();
                          }
                        },
                        itemBuilder: (context) => const [
                          PopupMenuItem(
                            value: _PhotoAction.editLocation,
                            child: _PhotoMenuLabel(
                              icon: Icons.edit_location_alt_outlined,
                              label: '위치 수정',
                            ),
                          ),
                          PopupMenuItem(
                            value: _PhotoAction.exclude,
                            child: _PhotoMenuLabel(
                              icon: Icons.hide_image_outlined,
                              label: '기록에서 제외',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                if (!photo.hasCoordinates)
                  const Positioned(
                    right: 6,
                    bottom: 6,
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                      ),
                      child: Padding(
                        padding: EdgeInsets.all(4),
                        child: Icon(
                          Icons.location_off_outlined,
                          size: 16,
                          color: ChiwawaColors.primary,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Text(
            time,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

enum _PhotoAction { editLocation, exclude }

class _PhotoMenuLabel extends StatelessWidget {
  const _PhotoMenuLabel({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 19),
        const SizedBox(width: ChiwawaSpacing.sm),
        Text(label),
      ],
    );
  }
}

class _EmptyDayPhotos extends StatelessWidget {
  const _EmptyDayPhotos();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: ChiwawaSpacing.lg),
      child: Text(
        '이 날짜에는 저장된 사진이 아직 없어요.',
        style: TextStyle(
          color: ChiwawaColors.textSecondary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
