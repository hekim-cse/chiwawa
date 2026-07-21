import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../shared/widgets/app_viewport.dart';

@immutable
class HomeMenuDestination {
  const HomeMenuDestination({
    required this.id,
    required this.label,
    required this.icon,
    required this.route,
  });

  final String id;
  final String label;
  final IconData icon;
  final String route;
}

const homeMenuDestinations = [
  HomeMenuDestination(
    id: 'trips',
    label: '내 여행',
    icon: Icons.luggage_rounded,
    route: '/trips',
  ),
  HomeMenuDestination(
    id: 'plan',
    label: 'AI 일정 설계',
    icon: Icons.route_rounded,
    route: '/plan',
  ),
  HomeMenuDestination(
    id: 'explore',
    label: '사진으로 장소 찾기',
    icon: Icons.camera_alt_rounded,
    route: '/explore',
  ),
  HomeMenuDestination(
    id: 'memorial',
    label: '여행 기록',
    icon: Icons.photo_album_rounded,
    route: '/memorial',
  ),
];

Future<void> showHomeMenuSheet(
  BuildContext context, {
  List<HomeMenuDestination> destinations = homeMenuDestinations,
}) {
  return showModalBottomSheet<void>(
    context: context,
    useSafeArea: true,
    constraints: const BoxConstraints(maxWidth: AppLayout.maxContentWidth),
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(
        top: Radius.circular(ChiwawaRadii.sheet),
      ),
    ),
    builder: (sheetContext) => Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 36,
            height: 4,
            margin: const EdgeInsets.only(bottom: 10),
            decoration: BoxDecoration(
              color: ChiwawaColors.textMuted,
              borderRadius: BorderRadius.circular(ChiwawaRadii.round),
            ),
          ),
          for (final destination in destinations)
            ListTile(
              key: ValueKey('home-menu-${destination.id}'),
              leading: Icon(destination.icon, color: ChiwawaColors.primary),
              title: Text(
                destination.label,
                style: Theme.of(context).textTheme.titleSmall,
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () {
                Navigator.pop(sheetContext);
                context.go(destination.route);
              },
            ),
        ],
      ),
    ),
  );
}
