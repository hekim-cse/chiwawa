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
              stops,
            );
            final markerIndexes = _markerIndexes(stops);
            return Stack(
              children: [
                Positioned.fill(
                  child: CustomPaint(
                    painter: _RouteMapPainter(points: points),
                  ),
                ),
                for (final index in markerIndexes)
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
                          _isRoundTripEndpoint(stops, index)
                              ? 'S/E'
                              : stops[index].stopType == 'START'
                                  ? 'S'
                                  : stops[index].stopType == 'END'
                                      ? 'E'
                                      : '${stops.take(index + 1).where((stop) => stop.stopType == 'POI').length}',
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

List<Offset> _routePoints(Size size, List<PlanItineraryStop> stops) {
  final count = stops.length;
  if (count <= 0) return const [];
  const fractions = [
    Offset(0.18, 0.73),
    Offset(0.36, 0.42),
    Offset(0.58, 0.58),
    Offset(0.79, 0.27),
    Offset(0.84, 0.73),
    Offset(0.55, 0.82),
  ];
  final points = <Offset>[];
  final firstIndexByPlaceId = <String, int>{};
  for (var index = 0; index < count; index++) {
    final placeId = stops[index].place.placeId.trim();
    final existingIndex = placeId.isEmpty ? null : firstIndexByPlaceId[placeId];
    if (existingIndex != null) {
      points.add(points[existingIndex]);
      continue;
    }
    final fraction = fractions[index % fractions.length];
    points.add(Offset(size.width * fraction.dx, size.height * fraction.dy));
    if (placeId.isNotEmpty) firstIndexByPlaceId[placeId] = index;
  }
  return points;
}

List<int> _markerIndexes(List<PlanItineraryStop> stops) {
  final indexes = <int>[];
  final seenPlaceIds = <String>{};
  for (var index = 0; index < stops.length; index++) {
    final placeId = stops[index].place.placeId.trim();
    if (placeId.isNotEmpty && !seenPlaceIds.add(placeId)) continue;
    indexes.add(index);
  }
  return indexes;
}

bool _isRoundTripEndpoint(List<PlanItineraryStop> stops, int index) {
  if (index != 0 || stops.length < 2) return false;
  final startId = stops.first.place.placeId.trim();
  return startId.isNotEmpty && startId == stops.last.place.placeId.trim();
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
