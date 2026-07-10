import '../models/memorial_map_models.dart';

const defaultClusterThreshold = 0.0008;

List<PawCluster> clusterPawPrints(
  List<MemorialPhotoPoint> points, {
  double threshold = defaultClusterThreshold,
}) {
  final sorted = [...points]..sort((a, b) => a.takenAt.compareTo(b.takenAt));
  final groups = <List<MemorialPhotoPoint>>[];

  for (final point in sorted) {
    final groupIndex = groups.indexWhere((group) {
      final center = _centerOf(group);
      return _coordinateDistanceSquared(
            point.latitude,
            point.longitude,
            center.$1,
            center.$2,
          ) <=
          threshold * threshold;
    });

    if (groupIndex == -1) {
      groups.add([point]);
    } else {
      groups[groupIndex].add(point);
      groups[groupIndex].sort((a, b) => a.takenAt.compareTo(b.takenAt));
    }
  }

  final clusters = <PawCluster>[];
  for (final group in groups) {
    final center = _centerOf(group);
    final first = group.first;
    clusters.add(
      PawCluster(
        id: 'paw-${first.id}',
        placeName: first.placeName,
        latitude: center.$1,
        longitude: center.$2,
        arrivalTime: first.takenAt,
        photos: List.unmodifiable(group),
      ),
    );
  }

  clusters.sort((a, b) => a.arrivalTime.compareTo(b.arrivalTime));
  return List.unmodifiable(clusters);
}

(double, double) _centerOf(List<MemorialPhotoPoint> points) {
  final latitude =
      points.fold<double>(0, (sum, point) => sum + point.latitude) /
          points.length;
  final longitude =
      points.fold<double>(0, (sum, point) => sum + point.longitude) /
          points.length;
  return (latitude, longitude);
}

double _coordinateDistanceSquared(
  double latitudeA,
  double longitudeA,
  double latitudeB,
  double longitudeB,
) {
  final latDelta = latitudeA - latitudeB;
  final lngDelta = longitudeA - longitudeB;
  return (latDelta * latDelta + lngDelta * lngDelta);
}
