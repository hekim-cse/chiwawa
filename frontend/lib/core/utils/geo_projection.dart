import 'dart:ui';

import '../models/memorial_map_models.dart';

class GeoBounds {
  const GeoBounds({
    required this.minLatitude,
    required this.maxLatitude,
    required this.minLongitude,
    required this.maxLongitude,
  });

  final double minLatitude;
  final double maxLatitude;
  final double minLongitude;
  final double maxLongitude;
}

GeoBounds boundsForClusters(List<PawCluster> clusters) {
  if (clusters.isEmpty) {
    return const GeoBounds(
      minLatitude: 0,
      maxLatitude: 0,
      minLongitude: 0,
      maxLongitude: 0,
    );
  }

  var minLatitude = clusters.first.latitude;
  var maxLatitude = clusters.first.latitude;
  var minLongitude = clusters.first.longitude;
  var maxLongitude = clusters.first.longitude;

  for (final cluster in clusters.skip(1)) {
    minLatitude = _min(minLatitude, cluster.latitude);
    maxLatitude = _max(maxLatitude, cluster.latitude);
    minLongitude = _min(minLongitude, cluster.longitude);
    maxLongitude = _max(maxLongitude, cluster.longitude);
  }

  return GeoBounds(
    minLatitude: minLatitude,
    maxLatitude: maxLatitude,
    minLongitude: minLongitude,
    maxLongitude: maxLongitude,
  );
}

Offset projectGeoToUnit(
  double latitude,
  double longitude,
  GeoBounds bounds, {
  double padding = 0.12,
}) {
  final latSpan = bounds.maxLatitude - bounds.minLatitude;
  final lngSpan = bounds.maxLongitude - bounds.minLongitude;
  final safePadding = padding.clamp(0.0, 0.45).toDouble();
  final available = 1 - safePadding * 2;

  final x = lngSpan == 0 ? 0.5 : (longitude - bounds.minLongitude) / lngSpan;
  final y = latSpan == 0 ? 0.5 : 1 - (latitude - bounds.minLatitude) / latSpan;

  return Offset(
    (safePadding + x * available).clamp(0.0, 1.0),
    (safePadding + y * available).clamp(0.0, 1.0),
  );
}

double _min(double a, double b) => a < b ? a : b;
double _max(double a, double b) => a > b ? a : b;
