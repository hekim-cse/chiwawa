import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../../app/theme.dart';
import 'paw_map_timeline.dart';

class PawRoutePainter extends CustomPainter {
  PawRoutePainter({
    required this.points,
    required this.animation,
    required this.timeline,
  }) : super(repaint: animation);

  final List<Offset> points;
  final Animation<double> animation;
  final PawMapTimeline timeline;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;

    final backgroundPaint = Paint()
      ..color = ChiwawaColors.border
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    final activePaint = Paint()
      ..color = ChiwawaColors.primary
      ..strokeWidth = 4
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    for (var index = 0; index < points.length - 1; index++) {
      canvas.drawLine(points[index], points[index + 1], backgroundPaint);
    }

    final scaled =
        timeline.routeProgress(animation.value) * (points.length - 1);
    for (var index = 0; index < points.length - 1; index++) {
      if (scaled <= index) break;
      final segmentProgress = (scaled - index).clamp(0.0, 1.0).toDouble();
      final end = Offset.lerp(
            points[index],
            points[index + 1],
            segmentProgress,
          ) ??
          points[index];
      canvas.drawLine(points[index], end, activePaint);
    }
  }

  @override
  bool shouldRepaint(covariant PawRoutePainter oldDelegate) {
    return oldDelegate.animation != animation ||
        oldDelegate.timeline.markerCount != timeline.markerCount ||
        !listEquals(oldDelegate.points, points);
  }
}
