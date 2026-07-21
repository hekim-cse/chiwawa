import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../shared/widgets/mascot_avatar.dart';

class HomeRecommendationCard extends StatelessWidget {
  const HomeRecommendationCard({required this.onTap, super.key});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 12, 14),
      decoration: BoxDecoration(
        color: ChiwawaColors.movementSurface,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '지금 주변에서 가볼 만한 곳은 어디일까요?',
                  style: TextStyle(
                    fontSize: 13,
                    height: 1.35,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                TextButton.icon(
                  style: TextButton.styleFrom(
                    foregroundColor: ChiwawaColors.movement,
                    padding: EdgeInsets.zero,
                    minimumSize: const Size(48, 36),
                  ),
                  onPressed: onTap,
                  icon: const Icon(Icons.auto_awesome_rounded, size: 17),
                  label: const Text('추천 보기'),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          const MascotAvatar(size: 72),
        ],
      ),
    );
  }
}
