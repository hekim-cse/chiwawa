import 'package:flutter/material.dart';

import '../../../../app/theme.dart';
import '../../../../core/models/memorial_map_models.dart';
import '../../../../core/utils/geo_projection.dart';
import '../../../../shared/widgets/mascot_avatar.dart';
import 'paw_map_timeline.dart';
import 'paw_marker.dart';
import 'paw_route_painter.dart';

class PawMapCanvas extends StatelessWidget {
  const PawMapCanvas({
    required this.clusters,
    required this.animation,
    required this.timeline,
    required this.onClusterTap,
    super.key,
  });

  final List<PawCluster> clusters;
  final Animation<double> animation;
  final PawMapTimeline timeline;
  final ValueChanged<PawCluster> onClusterTap;

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: AspectRatio(
        aspectRatio: 1.32,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final points = _projectedPoints(constraints.biggest);
            return ClipRRect(
              borderRadius: BorderRadius.circular(ChiwawaRadii.card),
              child: DecoratedBox(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Color(0xFFFFF7F9),
                      Color(0xFFF4FBFF),
                      Color(0xFFFFFBF2),
                    ],
                  ),
                ),
                child: Stack(
                  children: [
                    Positioned.fill(
                      child: CustomPaint(
                        painter: PawRoutePainter(
                          points: points,
                          animation: animation,
                          timeline: timeline,
                        ),
                      ),
                    ),
                    Positioned.fill(
                      child: AnimatedBuilder(
                        animation: animation,
                        builder: (context, _) {
                          final value = animation.value;
                          final mascotPosition =
                              timeline.mascotPosition(points, value);
                          final activeIndex = timeline.activeMarkerIndex(value);

                          return Stack(
                            children: [
                              for (var index = 0;
                                  index < clusters.length;
                                  index++)
                                PawMarker(
                                  cluster: clusters[index],
                                  position: points[index],
                                  arrivalProgress:
                                      timeline.markerProgress(index, value),
                                  isCurrent: activeIndex == index,
                                  onTap: () => onClusterTap(clusters[index]),
                                ),
                              Transform.translate(
                                offset: Offset(
                                  mascotPosition.dx - 18,
                                  mascotPosition.dy - 18,
                                ),
                                child: const Align(
                                  alignment: Alignment.topLeft,
                                  child: IgnorePointer(
                                    child: MascotAvatar(
                                      key: ValueKey('paw-map-mascot'),
                                      size: 36,
                                      padding: 2,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  List<Offset> _projectedPoints(Size size) {
    final bounds = boundsForClusters(clusters);
    return [
      for (final cluster in clusters) _projectCluster(cluster, bounds, size),
    ];
  }

  Offset _projectCluster(PawCluster cluster, GeoBounds bounds, Size size) {
    final projected = projectGeoToUnit(
      cluster.latitude,
      cluster.longitude,
      bounds,
    );
    return Offset(projected.dx * size.width, projected.dy * size.height);
  }
}
