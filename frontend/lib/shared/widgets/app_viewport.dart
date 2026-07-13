import 'package:flutter/material.dart';

abstract final class AppLayout {
  static const double maxContentWidth = 430;
}

class AppViewport extends StatelessWidget {
  const AppViewport({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(
          maxWidth: AppLayout.maxContentWidth,
        ),
        child: SizedBox.expand(child: child),
      ),
    );
  }
}
