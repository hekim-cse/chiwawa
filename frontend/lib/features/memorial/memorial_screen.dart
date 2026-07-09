import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/confirmed_route.dart';
import '../../core/models/travel_models.dart';
import '../../core/providers/data_providers.dart';
import '../../shared/widgets/async_value_view.dart';
import 'widgets/daily_section.dart';
import 'widgets/trip_summary_card.dart';

class MemorialScreen extends ConsumerWidget {
  const MemorialScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final confirmedRoute = ref.watch(confirmedRouteProvider);

    return AsyncValueView<MemorialData>(
      value: ref.watch(memorialDataProvider),
      onRetry: () => ref.invalidate(memorialDataProvider),
      builder: (data) => _body(
        context,
        data.tripInfo,
        data.summary,
        data.days,
        confirmedRoute,
      ),
    );
  }

  Widget _body(
    BuildContext context,
    TripInfo tripInfo,
    MemorialSummary memorialSummary,
    List<MemorialDay> memorialDays,
    List<RoutePlace> confirmedRoute,
  ) {
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
          TripSummaryCard(
            tripInfo: tripInfo,
            summary: memorialSummary,
          ),
          if (confirmedRoute.isNotEmpty) ...[
            const SizedBox(height: 20),
            _ConfirmedRoutePreview(places: confirmedRoute),
          ],
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

class _ConfirmedRoutePreview extends StatelessWidget {
  const _ConfirmedRoutePreview({required this.places});

  final List<RoutePlace> places;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(
                Icons.route_rounded,
                color: ChiwawaColors.primary,
                size: 20,
              ),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  '확정 일정 미리보기',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'AI 일정 설계에서 확정한 동선을 기록 흐름으로 이어봤어요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 12,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 12),
          for (var index = 0; index < places.length; index++) ...[
            _ConfirmedRouteRow(
              order: index + 1,
              place: places[index],
              isLast: index == places.length - 1,
            ),
          ],
        ],
      ),
    );
  }
}

class _ConfirmedRouteRow extends StatelessWidget {
  const _ConfirmedRouteRow({
    required this.order,
    required this.place,
    required this.isLast,
  });

  final int order;
  final RoutePlace place;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 28,
          child: Column(
            children: [
              CircleAvatar(
                radius: 12,
                backgroundColor: ChiwawaColors.secondary,
                child: Text(
                  '$order',
                  style: const TextStyle(
                    color: ChiwawaColors.primary,
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              if (!isLast)
                Container(
                  width: 1.4,
                  height: 28,
                  margin: const EdgeInsets.symmetric(vertical: 3),
                  color: ChiwawaColors.border,
                ),
            ],
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Padding(
            padding: EdgeInsets.only(bottom: isLast ? 0 : 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  place.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  '${place.category} · ${place.duration}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: ChiwawaColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
