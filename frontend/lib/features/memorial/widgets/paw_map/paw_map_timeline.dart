import 'dart:ui';

import 'paw_map_motion.dart';

class PawMapTimeline {
  const PawMapTimeline({required this.markerCount});

  final int markerCount;

  double rawRouteProgress(double value) {
    return _normalize(value, PawMapMotion.routeStart, PawMapMotion.routeEnd);
  }

  double routeProgress(double value) {
    final raw = rawRouteProgress(value);
    if (markerCount <= 1) return raw;

    final scaled = raw * (markerCount - 1);
    final segment = scaled.floor().clamp(0, markerCount - 2).toInt();
    final localProgress = (scaled - segment).clamp(0.0, 1.0).toDouble();
    final eased = PawMapMotion.routeCurve.transform(localProgress);
    return (segment + eased) / (markerCount - 1);
  }

  double markerProgress(int index, double value) {
    if (index < 0 || index >= markerCount) return 0;

    final fraction = markerCount <= 1 ? 0.0 : index / (markerCount - 1);
    final start = PawMapMotion.routeStart +
        (PawMapMotion.routeEnd - PawMapMotion.routeStart) * fraction;
    final end = (start + PawMapMotion.markerRevealSpan).clamp(0.0, 1.0);
    final normalized = _normalize(value, start, end);
    return PawMapMotion.markerCurve.transform(normalized);
  }

  int activeMarkerIndex(double value) {
    if (markerCount == 0 || value < PawMapMotion.routeStart) return -1;
    final raw = rawRouteProgress(value);
    return (raw * (markerCount - 1)).floor().clamp(0, markerCount - 1).toInt();
  }

  Offset mascotPosition(List<Offset> points, double value) {
    if (points.isEmpty) return Offset.zero;
    if (points.length == 1) return points.first;

    final progress = routeProgress(value);
    final scaled = progress * (points.length - 1);
    final segment = scaled.floor().clamp(0, points.length - 2).toInt();
    final localProgress = (scaled - segment).clamp(0.0, 1.0).toDouble();
    return Offset.lerp(points[segment], points[segment + 1], localProgress) ??
        points.first;
  }

  double _normalize(double value, double start, double end) {
    if (end <= start) return value >= end ? 1 : 0;
    return ((value - start) / (end - start)).clamp(0.0, 1.0).toDouble();
  }
}
