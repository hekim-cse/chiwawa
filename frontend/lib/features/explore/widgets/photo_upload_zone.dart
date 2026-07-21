import 'package:flutter/material.dart';

import '../../../app/theme.dart';

class PhotoUploadZone extends StatelessWidget {
  const PhotoUploadZone({
    required this.onTap,
    this.compact = false,
    super.key,
  });

  final VoidCallback onTap;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: CustomPaint(
        painter: const _DashedBorderPainter(
          color: ChiwawaColors.textMuted,
          radius: 16,
        ),
        child: Container(
          height: compact ? 88 : 200,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          alignment: Alignment.center,
          child: compact
              ? const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.add_photo_alternate_rounded,
                      size: 28,
                      color: ChiwawaColors.textMuted,
                    ),
                    SizedBox(width: 10),
                    Text(
                      '다른 사진 분석',
                      style: TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                )
              : const Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.camera_alt,
                      size: 48,
                      color: ChiwawaColors.textMuted,
                    ),
                    SizedBox(height: 12),
                    Text(
                      '사진을 올려 장소를 찾아보세요',
                      style: TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}

class _DashedBorderPainter extends CustomPainter {
  const _DashedBorderPainter({required this.color, required this.radius});

  final Color color;
  final double radius;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke;
    final rect = RRect.fromRectAndRadius(
      Offset.zero & size,
      Radius.circular(radius),
    );
    final path = Path()..addRRect(rect);
    final metric = path.computeMetrics().first;
    const dash = 8.0;
    const gap = 6.0;
    var distance = 0.0;

    while (distance < metric.length) {
      final segment = metric.extractPath(distance, distance + dash);
      canvas.drawPath(segment, paint);
      distance += dash + gap;
    }
  }

  @override
  bool shouldRepaint(covariant _DashedBorderPainter oldDelegate) {
    return oldDelegate.color != color || oldDelegate.radius != radius;
  }
}
