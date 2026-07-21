import 'package:flutter/material.dart';

abstract final class AppLayout {
  static const double maxContentWidth = 430;

  static double pageHorizontalPadding(BuildContext context) {
    return MediaQuery.sizeOf(context).width <= 340 ? 16 : 20;
  }

  static EdgeInsets pageInsets(
    BuildContext context, {
    double top = 20,
    double bottom = 112,
  }) {
    final horizontal = pageHorizontalPadding(context);
    return EdgeInsets.fromLTRB(horizontal, top, horizontal, bottom);
  }
}

class AppViewport extends StatelessWidget {
  const AppViewport({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Theme.of(context).scaffoldBackgroundColor,
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(
            maxWidth: AppLayout.maxContentWidth,
          ),
          child: SizedBox.expand(child: child),
        ),
      ),
    );
  }
}
