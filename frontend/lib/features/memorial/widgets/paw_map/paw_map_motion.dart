import 'package:flutter/animation.dart';

abstract final class PawMapMotion {
  static const minimumDuration = Duration(milliseconds: 2200);
  static const maximumDuration = Duration(milliseconds: 3400);
  static const baseDuration = Duration(milliseconds: 1800);
  static const perAdditionalStop = Duration(milliseconds: 450);
  static const replayTransition = Duration(milliseconds: 180);

  static const double entranceEnd = 0.08;
  static const double routeStart = 0.10;
  static const double routeEnd = 0.88;
  static const double markerRevealSpan = 0.06;
  static const double restingMarkerOpacity = 0.34;
  static const double restingMarkerScale = 0.86;

  static const Curve entranceCurve = Curves.easeOutCubic;
  static const Curve routeCurve = Curves.easeInOutCubic;
  static const Curve markerCurve = Curves.easeOutCubic;

  static Duration totalDurationFor(int stopCount) {
    final extraStops = stopCount > 1 ? stopCount - 1 : 0;
    final milliseconds = baseDuration.inMilliseconds +
        perAdditionalStop.inMilliseconds * extraStops;
    final clamped = milliseconds.clamp(
      minimumDuration.inMilliseconds,
      maximumDuration.inMilliseconds,
    );
    return Duration(milliseconds: clamped.toInt());
  }
}
