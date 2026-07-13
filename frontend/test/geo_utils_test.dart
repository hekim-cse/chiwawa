import 'package:flutter_test/flutter_test.dart';
import 'package:chiwawa/core/models/memorial_map_models.dart';
import 'package:chiwawa/core/utils/geo_cluster.dart';
import 'package:chiwawa/core/utils/geo_projection.dart';

void main() {
  MemorialPhotoPoint point({
    required String id,
    required DateTime takenAt,
    required double latitude,
    required double longitude,
    String placeName = '테스트 장소',
  }) {
    return MemorialPhotoPoint(
      id: id,
      takenAt: takenAt,
      latitude: latitude,
      longitude: longitude,
      placeName: placeName,
      assetPath: 'assets/images/mock/mock_memorial_01.png',
    );
  }

  test('MemorialPhotoPoint parses and serializes backend fields', () {
    final parsed = MemorialPhotoPoint.fromJson(const {
      'id': 'photo-1',
      'taken_at': '2025-04-03T10:20:00',
      'latitude': 35.7148,
      'longitude': 139.7967,
      'place_name': '아사쿠사 센소지',
      'asset_path': 'assets/images/mock/mock_memorial_01.png',
    });

    expect(parsed.id, 'photo-1');
    expect(parsed.placeName, '아사쿠사 센소지');
    expect(parsed.toJson()['latitude'], 35.7148);
  });

  test('MemorialPhotoPoint throws when coordinates are missing', () {
    expect(
      () => MemorialPhotoPoint.fromJson(const {
        'id': 'photo-1',
        'taken_at': '2025-04-03T10:20:00',
        'place_name': '좌표 없는 사진',
      }),
      throwsFormatException,
    );
  });

  test('clusterPawPrints groups nearby photos and keeps arrival order', () {
    final clusters = clusterPawPrints([
      point(
        id: 'far',
        takenAt: DateTime(2025, 4, 3, 13),
        latitude: 35.66,
        longitude: 139.70,
        placeName: '시부야',
      ),
      point(
        id: 'near-2',
        takenAt: DateTime(2025, 4, 3, 9, 12),
        latitude: 35.7149,
        longitude: 139.7968,
        placeName: '아사쿠사',
      ),
      point(
        id: 'near-1',
        takenAt: DateTime(2025, 4, 3, 9),
        latitude: 35.7148,
        longitude: 139.7967,
        placeName: '아사쿠사',
      ),
    ]);

    expect(clusters, hasLength(2));
    expect(clusters.first.placeName, '아사쿠사');
    expect(clusters.first.photoCount, 2);
    expect(clusters.last.placeName, '시부야');
  });

  test('projectGeoToUnit keeps coordinates within padded unit bounds', () {
    final clusters = [
      PawCluster(
        id: 'a',
        placeName: 'A',
        latitude: 35,
        longitude: 139,
        arrivalTime: DateTime(2025),
        photos: const [],
      ),
      PawCluster(
        id: 'b',
        placeName: 'B',
        latitude: 36,
        longitude: 140,
        arrivalTime: DateTime(2025),
        photos: const [],
      ),
    ];

    final bounds = boundsForClusters(clusters);
    final projected = projectGeoToUnit(35, 139, bounds);

    expect(projected.dx, closeTo(0.12, 0.001));
    expect(projected.dy, closeTo(0.88, 0.001));
  });

  test('projectGeoToUnit centers points when all coordinates are identical',
      () {
    const bounds = GeoBounds(
      minLatitude: 35,
      maxLatitude: 35,
      minLongitude: 139,
      maxLongitude: 139,
    );

    expect(projectGeoToUnit(35, 139, bounds), const Offset(0.5, 0.5));
  });
}
