import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import 'app_viewport.dart';

class BottomNavBar extends StatelessWidget {
  const BottomNavBar({super.key});

  static const _items = [
    _NavItem('홈', Icons.home, '/home'),
    _NavItem('일정', Icons.map, '/plan'),
    _NavItem('탐색', Icons.camera_alt, '/explore'),
    _NavItem('기록', Icons.photo_album, '/memorial'),
    _NavItem('마이', Icons.person, '/mypage'),
  ];

  @override
  Widget build(BuildContext context) {
    final currentLocation = GoRouterState.of(context).uri.path;
    final isNarrow = MediaQuery.sizeOf(context).width <= 340;
    final matchedIndex = _items.indexWhere(
      (item) => currentLocation.startsWith(item.path),
    );
    final currentIndex = currentLocation.startsWith('/trips')
        ? 4
        : matchedIndex == -1
            ? 0
            : matchedIndex;

    return DecoratedBox(
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: ChiwawaColors.border)),
      ),
      child: SafeArea(
        top: false,
        child: Center(
          heightFactor: 1,
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: AppLayout.maxContentWidth,
            ),
            child: isNarrow
                ? _CompactBottomNav(
                    items: _items,
                    currentIndex: currentIndex,
                    onSelected: (index) => context.go(_items[index].path),
                  )
                : NavigationBar(
                    height: ChiwawaControlSizes.navigationBar,
                    selectedIndex: currentIndex,
                    labelBehavior:
                        NavigationDestinationLabelBehavior.alwaysShow,
                    indicatorColor: ChiwawaColors.secondary,
                    indicatorShape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(ChiwawaRadii.control),
                    ),
                    backgroundColor: Colors.white,
                    surfaceTintColor: Colors.transparent,
                    onDestinationSelected: (index) {
                      context.go(_items[index].path);
                    },
                    destinations: [
                      for (final item in _items)
                        NavigationDestination(
                          icon: Icon(
                            item.icon,
                            color: ChiwawaColors.textMuted,
                          ),
                          selectedIcon: Icon(
                            item.icon,
                            color: ChiwawaColors.primary,
                          ),
                          label: item.label,
                        ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}

class _CompactBottomNav extends StatelessWidget {
  const _CompactBottomNav({
    required this.items,
    required this.currentIndex,
    required this.onSelected,
  });

  final List<_NavItem> items;
  final int currentIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: ChiwawaControlSizes.navigationBar,
      child: Row(
        children: [
          for (var index = 0; index < items.length; index++)
            Expanded(
              child: Semantics(
                button: true,
                selected: index == currentIndex,
                label: items[index].label,
                child: InkWell(
                  onTap: () => onSelected(index),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        items[index].icon,
                        size: 21,
                        color: index == currentIndex
                            ? ChiwawaColors.primary
                            : ChiwawaColors.textMuted,
                      ),
                      const SizedBox(height: 3),
                      if (index == currentIndex)
                        Text(
                          items[index].label,
                          maxLines: 1,
                          style:
                              Theme.of(context).textTheme.labelMedium?.copyWith(
                                    color: ChiwawaColors.primary,
                                  ),
                        )
                      else
                        const SizedBox(height: 15),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _NavItem {
  const _NavItem(this.label, this.icon, this.path);

  final String label;
  final IconData icon;
  final String path;
}
