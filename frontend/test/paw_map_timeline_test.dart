import 'package:flutter_test/flutter_test.dart';

import 'package:chiwawa/features/memorial/widgets/paw_map/paw_map_motion.dart';
import 'package:chiwawa/features/memorial/widgets/paw_map/paw_map_timeline.dart';

void main() {
  test('paw map duration scales with stops and stays within limits', () {
    expect(
      PawMapMotion.totalDurationFor(1),
      const Duration(milliseconds: 2200),
    );
    expect(
      PawMapMotion.totalDurationFor(3),
      const Duration(milliseconds: 2700),
    );
    expect(
      PawMapMotion.totalDurationFor(20),
      const Duration(milliseconds: 3400),
    );
  });

  test('paw map timeline reveals markers in route order', () {
    const timeline = PawMapTimeline(markerCount: 3);

    expect(timeline.markerProgress(0, 0), 0);
    expect(
      timeline.markerProgress(
        0,
        PawMapMotion.routeStart + PawMapMotion.markerRevealSpan,
      ),
      1,
    );
    expect(timeline.markerProgress(2, 0.5), 0);
    expect(timeline.markerProgress(2, 1), 1);
  });

  test('paw map timeline moves mascot through each waypoint', () {
    const timeline = PawMapTimeline(markerCount: 3);
    const points = [
      Offset(0, 0),
      Offset(10, 0),
      Offset(10, 10),
    ];

    expect(
      timeline.mascotPosition(points, PawMapMotion.routeStart),
      points.first,
    );
    expect(
      timeline.mascotPosition(
        points,
        (PawMapMotion.routeStart + PawMapMotion.routeEnd) / 2,
      ),
      points[1],
    );
    expect(
      timeline.mascotPosition(points, PawMapMotion.routeEnd),
      points.last,
    );
  });

  test('paw map timeline exposes only the latest reached marker as active', () {
    const timeline = PawMapTimeline(markerCount: 4);

    expect(timeline.activeMarkerIndex(0), -1);
    expect(timeline.activeMarkerIndex(PawMapMotion.routeStart), 0);
    expect(timeline.activeMarkerIndex(PawMapMotion.routeEnd), 3);
  });
}
