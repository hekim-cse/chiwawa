import 'package:flutter/material.dart';

import '../../../app/theme.dart';

@immutable
class HomeQuickActionData {
  const HomeQuickActionData({
    required this.id,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final String id;
  final IconData icon;
  final String label;
  final VoidCallback onTap;
}

class HomeQuickActions extends StatelessWidget {
  const HomeQuickActions({required this.actions, super.key});

  final List<HomeQuickActionData> actions;

  @override
  Widget build(BuildContext context) {
    if (actions.isEmpty) return const SizedBox.shrink();

    return LayoutBuilder(
      builder: (context, constraints) {
        final columnCount = constraints.maxWidth < 320 ? 2 : 3;
        final rowCount = (actions.length / columnCount).ceil();
        final height = rowCount * 76.0;

        return SizedBox(
          height: height,
          child: GridView.builder(
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: columnCount,
              mainAxisExtent: 76,
            ),
            itemCount: actions.length,
            itemBuilder: (context, index) {
              final action = actions[index];
              return _QuickActionCell(
                key: ValueKey('home-quick-action-${action.id}'),
                action: action,
              );
            },
          ),
        );
      },
    );
  }
}

class _QuickActionCell extends StatelessWidget {
  const _QuickActionCell({
    required this.action,
    super.key,
  });

  final HomeQuickActionData action;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(ChiwawaRadii.control),
      onTap: action.onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 9),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(action.icon, color: ChiwawaColors.primary, size: 23),
            const SizedBox(height: 6),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                action.label,
                maxLines: 1,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
