import 'package:flutter/material.dart';

import '../../app/theme.dart';

class BottomSheetBase extends StatelessWidget {
  const BottomSheetBase({
    required this.children,
    this.padding = const EdgeInsets.fromLTRB(20, 12, 20, 24),
    super.key,
  });

  final List<Widget> children;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(ChiwawaRadii.sheet),
        ),
      ),
      child: Padding(
        padding: padding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 44,
                height: 4,
                margin: const EdgeInsets.only(bottom: 18),
                decoration: BoxDecoration(
                  color: ChiwawaColors.border,
                  borderRadius: BorderRadius.circular(ChiwawaRadii.round),
                ),
              ),
            ),
            ...children,
          ],
        ),
      ),
    );
  }
}
