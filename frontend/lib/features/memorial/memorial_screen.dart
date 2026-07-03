import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../core/mock_data.dart';
import 'widgets/daily_section.dart';
import 'widgets/trip_summary_card.dart';

class MemorialScreen extends StatelessWidget {
  const MemorialScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
        children: [
          Text(
            '여행 마무리',
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 6),
          const Text(
            '사진과 이동 동선을 자동으로 정리했어요.',
            style: TextStyle(color: ChiwawaColors.textSecondary),
          ),
          const SizedBox(height: 18),
          const TripSummaryCard(
            tripInfo: tripInfo,
            summary: memorialSummary,
          ),
          const SizedBox(height: 20),
          for (var index = 0; index < memorialDays.length; index++) ...[
            DailySection(day: memorialDays[index], seedOffset: index * 20),
            const SizedBox(height: 18),
          ],
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.share, size: 18),
                  label: const Text('공유하기'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {},
                  icon: const Icon(Icons.download, size: 18),
                  label: const Text('앨범 내보내기'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
