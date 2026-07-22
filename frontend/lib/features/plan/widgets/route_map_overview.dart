import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../models/plan_itinerary.dart';

class RouteMapOverview extends StatelessWidget {
  const RouteMapOverview({required this.stops, super.key});

  final List<PlanItineraryStop> stops;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(ChiwawaRadii.card),
      child: SizedBox(
        height: 224,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final points = _routePoints(
              Size(constraints.maxWidth, constraints.maxHeight),
              stops.length,
            );
            return Stack(
              children: [
                Positioned.fill(
                  child: CustomPaint(
                    painter: _RouteMapPainter(points: points),
                  ),
                ),
                for (var index = 0; index < points.length; index++)
                  Positioned(
                    left: points[index].dx - 17,
                    top: points[index].dy - 17,
                    child: Tooltip(
                      message: stops[index].place.name,
                      child: Container(
                        key: ValueKey('route-map-marker-${stops[index].id}'),
                        width: 34,
                        height: 34,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: index == 0
                              ? ChiwawaColors.movement
                              : ChiwawaColors.primary,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 3),
                          boxShadow: const [
                            BoxShadow(
                              color: Color(0x29000000),
                              blurRadius: 8,
                              offset: Offset(0, 3),
                            ),
                          ],
                        ),
                        child: Text(
                          '${index + 1}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

List<Offset> _routePoints(Size size, int count) {
  if (count <= 0) return const [];
  const fractions = [
    Offset(0.18, 0.73),
    Offset(0.36, 0.42),
    Offset(0.58, 0.58),
    Offset(0.79, 0.27),
    Offset(0.84, 0.73),
    Offset(0.55, 0.82),
  ];
  return [
    for (var index = 0; index < count; index++)
      Offset(
        size.width * fractions[index % fractions.length].dx,
        size.height * fractions[index % fractions.length].dy,
      ),
  ];
}

class _RouteMapPainter extends CustomPainter {
  const _RouteMapPainter({required this.points});

  final List<Offset> points;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(
      Offset.zero & size,
      Paint()..color = ChiwawaColors.mapLand,
    );

    final water = Path()
      ..moveTo(size.width * 0.64, 0)
      ..cubicTo(
        size.width * 0.74,
        size.height * 0.27,
        size.width * 0.66,
        size.height * 0.68,
        size.width,
        size.height * 0.56,
      )
      ..lineTo(size.width, 0)
      ..close();
    canvas.drawPath(water, Paint()..color = ChiwawaColors.mapWater);

    final roadPaint = Paint()
      ..color = Colors.white
      ..strokeWidth = 5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    for (var index = 0; index < 5; index++) {
      final y = size.height * (0.16 + index * 0.17);
      final wave = Path()
        ..moveTo(-12, y)
        ..quadraticBezierTo(
          size.width * 0.45,
          y + (index.isEven ? 28 : -24),
          size.width + 12,
          y + 8,
        );
      canvas.drawPath(wave, roadPaint);
    }

    if (points.length < 2) return;
    final route = Path()..moveTo(points.first.dx, points.first.dy);
    for (var index = 1; index < points.length; index++) {
      final previous = points[index - 1];
      final point = points[index];
      final control = Offset(
        (previous.dx + point.dx) / 2,
        math.min(previous.dy, point.dy) - 18,
      );
      route.quadraticBezierTo(control.dx, control.dy, point.dx, point.dy);
    }
    canvas.drawPath(
      route,
      Paint()
        ..color = Colors.white
        ..strokeWidth = 7
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round,
    );
    canvas.drawPath(
      route,
      Paint()
        ..color = ChiwawaColors.primary
        ..strokeWidth = 3
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(covariant _RouteMapPainter oldDelegate) {
    return oldDelegate.points != points;
  }
}
