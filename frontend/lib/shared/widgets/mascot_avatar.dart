import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../core/assets/app_images.dart';

class MascotAvatar extends StatelessWidget {
  const MascotAvatar({
    this.size = 48,
    this.padding = 3,
    super.key,
  });

  final double size;
  final double padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(padding),
      decoration: const BoxDecoration(
        color: ChiwawaColors.secondary,
        shape: BoxShape.circle,
      ),
      clipBehavior: Clip.antiAlias,
      child: Image.asset(
        AppImages.mascot,
        fit: BoxFit.contain,
        semanticLabel: '치와와 마스코트',
      ),
    );
  }
}
