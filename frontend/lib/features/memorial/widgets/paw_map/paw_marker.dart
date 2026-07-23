import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../app/theme.dart';
import '../../../../core/models/memorial_map_models.dart';
import 'paw_map_motion.dart';

class PawMarker extends StatelessWidget {
  const PawMarker({
    required this.cluster,
    required this.position,
    required this.arrivalProgress,
    required this.isCurrent,
    required this.onTap,
    super.key,
  });

  final PawCluster cluster;
  final Offset position;
  final double arrivalProgress;
  final bool isCurrent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final progress = arrivalProgress.clamp(0.0, 1.0).toDouble();
    final opacity = lerpDouble(
          PawMapMotion.restingMarkerOpacity,
          1,
          progress,
        ) ??
        1;
    final scale = lerpDouble(
          PawMapMotion.restingMarkerScale,
          1,
          progress,
        ) ??
        1;
    final colorAlpha = (255 * opacity).round();
    final shadowBaseAlpha = isCurrent ? 0x33 : 0x1F;

    return Positioned(
      left: position.dx - ChiwawaControlSizes.minimumInteractive / 2,
      top: position.dy - ChiwawaControlSizes.minimumInteractive / 2,
      child: Semantics(
        label: '${cluster.placeName} 발자국, 사진 ${cluster.photoCount}장',
        button: true,
        child: GestureDetector(
          key: ValueKey('paw-marker-${cluster.id}'),
          behavior: HitTestBehavior.opaque,
          onTap: onTap,
          child: SizedBox(
            width: ChiwawaControlSizes.minimumInteractive,
            height: ChiwawaControlSizes.minimumInteractive,
            child: Center(
              child: Transform.scale(
                scale: scale,
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: Colors.white.withAlpha(colorAlpha),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: ChiwawaColors.primary.withAlpha(colorAlpha),
                      width: isCurrent ? 2 : 1,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Color.fromARGB(
                          (shadowBaseAlpha * opacity).round(),
                          0xE4,
                          0x5F,
                          0x78,
                        ),
                        blurRadius: isCurrent ? 14 : 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.pets_rounded,
                    color: ChiwawaColors.primary.withAlpha(colorAlpha),
                    size: 20,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
