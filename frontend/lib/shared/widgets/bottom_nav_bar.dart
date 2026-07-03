import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';

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
    final matchedIndex = _items.indexWhere(
      (item) => currentLocation.startsWith(item.path),
    );
    final currentIndex = matchedIndex == -1 ? 0 : matchedIndex;

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
            constraints: const BoxConstraints(maxWidth: 430),
            child: NavigationBar(
              height: 64,
              selectedIndex: currentIndex,
              labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
              indicatorColor: Colors.transparent,
              backgroundColor: Colors.white,
              onDestinationSelected: (index) {
                context.go(_items[index].path);
              },
              destinations: [
                for (final item in _items)
                  NavigationDestination(
                    icon: Icon(item.icon, color: ChiwawaColors.textMuted),
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

class _NavItem {
  const _NavItem(this.label, this.icon, this.path);

  final String label;
  final IconData icon;
  final String path;
}
