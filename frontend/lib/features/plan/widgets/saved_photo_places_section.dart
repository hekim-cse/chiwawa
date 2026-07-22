import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';

class SavedPhotoPlacesSection extends StatelessWidget {
  const SavedPhotoPlacesSection({
    required this.places,
    required this.selectedPlaces,
    required this.onSelect,
    required this.onRemove,
    super.key,
  });

  final List<PhotoSearchResult> places;
  final List<String> selectedPlaces;
  final ValueChanged<PhotoSearchResult> onSelect;
  final ValueChanged<PhotoSearchResult> onRemove;

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
          const Row(
            children: [
              Icon(
                Icons.camera_alt_rounded,
                color: ChiwawaColors.primary,
                size: 20,
              ),
              SizedBox(width: 8),
              Text(
                '사진으로 저장한 장소',
                style: TextStyle(
                  color: ChiwawaColors.textPrimary,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            '사진 탐색에서 찾은 장소를 일정 후보로 바로 넣어보세요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final place in places)
                _SavedPhotoPlaceChip(
                  key: ValueKey('saved-photo-place-${place.identityKey}'),
                  place: place,
                  selected: selectedPlaces.contains(place.name),
                  onSelect: () => onSelect(place),
                  onRemove: () => onRemove(place),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SavedPhotoPlaceChip extends StatelessWidget {
  const _SavedPhotoPlaceChip({
    required this.place,
    required this.selected,
    required this.onSelect,
    required this.onRemove,
    super.key,
  });

  final PhotoSearchResult place;
  final bool selected;
  final VoidCallback onSelect;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: ChiwawaColors.secondary,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(99),
        side: const BorderSide(color: ChiwawaColors.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            key: ValueKey('select-saved-place-${place.name}'),
            onTap: onSelect,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 44),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(10, 7, 6, 7),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      selected
                          ? Icons.check_circle_rounded
                          : Icons.add_location_alt_rounded,
                      color: ChiwawaColors.primary,
                      size: 17,
                    ),
                    const SizedBox(width: 5),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 180),
                      child: Text(
                        place.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: ChiwawaColors.textPrimary,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Tooltip(
            message: '${place.name} 저장 목록에서 삭제',
            child: InkWell(
              key: ValueKey('remove-saved-place-${place.name}'),
              onTap: onRemove,
              child: const SizedBox(
                width: 44,
                height: 44,
                child: Icon(
                  Icons.close_rounded,
                  color: ChiwawaColors.primary,
                  size: 16,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
