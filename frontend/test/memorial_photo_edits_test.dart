import 'package:chiwawa/core/models/memorial_models.dart';
import 'package:chiwawa/features/memorial/memorial_photo_edits_controller.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final photo = MemorialPhoto(
    id: 'photo-1',
    fileName: 'photo.jpg',
    contentType: 'image/jpeg',
    takenAt: DateTime(2026, 7, 14, 10),
    fileUrl: '',
    latitude: 35.0,
    longitude: 139.0,
    address: '이전 위치',
  );

  test('location edit changes the visible timeline without mutating source',
      () {
    final source = MemorialDayTimeline(
      day: DateTime(2026, 7, 14),
      items: [MemorialTimelineEntry(seq: 0, photo: photo)],
    );
    const edits = {
      'photo-1': MemorialPhotoEdit(
        address: '수정한 위치',
        latitude: 35.5,
        longitude: 139.5,
      ),
    };

    final edited = applyMemorialPhotoEdits(source, edits);

    expect(edited.items.single.photo.address, '수정한 위치');
    expect(edited.items.single.photo.latitude, 35.5);
    expect(source.items.single.photo.address, '이전 위치');
  });

  test('excluded photos are removed from the visible timeline', () {
    final source = MemorialDayTimeline(
      day: DateTime(2026, 7, 14),
      items: [MemorialTimelineEntry(seq: 0, photo: photo)],
    );

    final edited = applyMemorialPhotoEdits(
      source,
      const {'photo-1': MemorialPhotoEdit(excluded: true)},
    );

    expect(edited.items, isEmpty);
  });
}
