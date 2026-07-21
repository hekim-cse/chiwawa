import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/auth/auth_controller.dart';
import '../../core/models/memorial_map_models.dart';
import '../../core/models/memorial_models.dart';
import '../../core/providers/data_providers.dart';
import '../../core/services/trip_session_service.dart';
import '../../core/utils/geo_cluster.dart';

class MemorialPhotoEdit {
  const MemorialPhotoEdit({
    this.excluded = false,
    this.latitude,
    this.longitude,
    this.address,
  });

  final bool excluded;
  final double? latitude;
  final double? longitude;
  final String? address;

  MemorialPhotoEdit copyWith({
    bool? excluded,
    double? latitude,
    double? longitude,
    String? address,
  }) {
    return MemorialPhotoEdit(
      excluded: excluded ?? this.excluded,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      address: address ?? this.address,
    );
  }
}

final memorialPhotoEditsProvider = StateNotifierProvider<
    MemorialPhotoEditsController, Map<String, MemorialPhotoEdit>>((ref) {
  ref.watch(authSessionRevisionProvider);
  ref.watch(currentTripRevisionProvider);
  return MemorialPhotoEditsController();
});

final editedMemorialDayProvider =
    Provider.family<AsyncValue<MemorialDayTimeline>, DateTime>((ref, date) {
  final timeline = ref.watch(memorialDayProvider(date));
  final edits = ref.watch(memorialPhotoEditsProvider);
  return timeline.whenData((value) => applyMemorialPhotoEdits(value, edits));
});

final editedPawMapProvider =
    Provider.family<AsyncValue<List<PawCluster>>, DateTime>((ref, date) {
  return ref.watch(editedMemorialDayProvider(date)).whenData((timeline) {
    final points = <MemorialPhotoPoint>[
      for (final entry in timeline.items)
        if (entry.photo.hasCoordinates)
          MemorialPhotoPoint(
            id: entry.photo.id,
            takenAt: entry.photo.takenAt,
            latitude: entry.photo.latitude!,
            longitude: entry.photo.longitude!,
            placeName: entry.photo.address?.trim().isNotEmpty == true
                ? entry.photo.address!.trim()
                : '위치 정보 없음',
            assetPath: entry.photo.assetPath,
            fileUrl: entry.photo.fileUrl,
          ),
    ];
    return clusterPawPrints(points);
  });
});

class MemorialPhotoEditsController
    extends StateNotifier<Map<String, MemorialPhotoEdit>> {
  MemorialPhotoEditsController() : super(const {});

  void exclude(String photoId) {
    final current = state[photoId] ?? const MemorialPhotoEdit();
    state = Map.unmodifiable({
      ...state,
      photoId: current.copyWith(excluded: true),
    });
  }

  void restore(String photoId) {
    final current = state[photoId];
    if (current == null) return;
    state = Map.unmodifiable({
      ...state,
      photoId: current.copyWith(excluded: false),
    });
  }

  void updateLocation(
    String photoId, {
    required String address,
    required double latitude,
    required double longitude,
  }) {
    final current = state[photoId] ?? const MemorialPhotoEdit();
    state = Map.unmodifiable({
      ...state,
      photoId: current.copyWith(
        address: address,
        latitude: latitude,
        longitude: longitude,
      ),
    });
  }
}

MemorialDayTimeline applyMemorialPhotoEdits(
  MemorialDayTimeline timeline,
  Map<String, MemorialPhotoEdit> edits,
) {
  return MemorialDayTimeline(
    day: timeline.day,
    items: List.unmodifiable([
      for (final entry in timeline.items)
        if (!(edits[entry.photo.id]?.excluded ?? false))
          MemorialTimelineEntry(
            seq: entry.seq,
            photo: _applyEdit(entry.photo, edits[entry.photo.id]),
          ),
    ]),
  );
}

MemorialPhoto _applyEdit(MemorialPhoto photo, MemorialPhotoEdit? edit) {
  if (edit == null) return photo;
  return MemorialPhoto(
    id: photo.id,
    fileName: photo.fileName,
    contentType: photo.contentType,
    takenAt: photo.takenAt,
    fileUrl: photo.fileUrl,
    latitude: edit.latitude ?? photo.latitude,
    longitude: edit.longitude ?? photo.longitude,
    address: edit.address ?? photo.address,
    memo: photo.memo,
    createdAt: photo.createdAt,
    assetPath: photo.assetPath,
  );
}
