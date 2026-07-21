import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../../../shared/widgets/mascot_avatar.dart';

class HomeHeader extends StatelessWidget {
  const HomeHeader({
    required this.tripInfo,
    required this.onMenuTap,
    required this.onTripTap,
    super.key,
  });

  final TripInfo tripInfo;
  final VoidCallback onMenuTap;
  final VoidCallback onTripTap;

  @override
  Widget build(BuildContext context) {
    final tripSummary = [
      tripInfo.tripName,
      tripInfo.weather,
    ].where((value) => value.trim().isNotEmpty).join(' · ');

    return Column(
      children: [
        Row(
          children: [
            _HeaderIconButton(
              icon: Icons.menu,
              tooltip: '메뉴',
              onTap: onMenuTap,
            ),
            const Expanded(
              child: Center(
                child: Text(
                  '치와와',
                  style: TextStyle(
                    color: ChiwawaColors.primary,
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),
            _HeaderIconButton(
              icon: Icons.luggage_rounded,
              tooltip: '내 여행',
              onTap: onTripTap,
            ),
          ],
        ),
        const SizedBox(height: ChiwawaSpacing.md),
        Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(ChiwawaRadii.control),
            onTap: onTripTap,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(2, 8, 2, 8),
              child: Row(
                children: [
                  const MascotAvatar(size: 52),
                  const SizedBox(width: ChiwawaSpacing.sm),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '복잡한 건 치와 두고 일단 와',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: ChiwawaSpacing.xxs),
                        Text(
                          tripSummary,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: ChiwawaColors.textSecondary,
                                  ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: ChiwawaSpacing.xs),
                  const Icon(
                    Icons.chevron_right_rounded,
                    color: ChiwawaColors.textMuted,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _HeaderIconButton extends StatelessWidget {
  const _HeaderIconButton({
    required this.icon,
    required this.onTap,
    required this.tooltip,
  });

  final IconData icon;
  final VoidCallback onTap;
  final String tooltip;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: SizedBox(
          width: 44,
          height: 44,
          child: Icon(icon, color: ChiwawaColors.textPrimary, size: 24),
        ),
      ),
    );
  }
}
