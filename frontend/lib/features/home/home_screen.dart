import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/assets/app_images.dart';
import '../../core/models/travel_models.dart';
import '../../core/providers/data_providers.dart';
import '../assist/widgets/free_time_sheet.dart';
import '../../shared/widgets/async_value_view.dart';
import '../../shared/widgets/mascot_avatar.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AsyncValueView<HomeData>(
      value: ref.watch(homeDataProvider),
      onRetry: () => ref.invalidate(homeDataProvider),
      builder: (data) => _body(context, data.tripInfo, data.schedules),
    );
  }

  Widget _body(
    BuildContext context,
    TripInfo tripInfo,
    List<ScheduleItem> schedules,
  ) {
    return SafeArea(
      child: SizedBox.expand(
        child: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Color(0xFFFFF6F8),
                Color(0xFFFFFBFC),
                ChiwawaColors.background,
              ],
            ),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final contentWidth =
                  constraints.maxWidth > 430 ? 430.0 : constraints.maxWidth;

              return Align(
                alignment: Alignment.topCenter,
                child: SizedBox(
                  width: contentWidth,
                  height: constraints.maxHeight,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                    children: [
                      _HomeHeader(
                        tripInfo: tripInfo,
                        onMenuTap: () =>
                            _showHomeSnackBar(context, '메뉴는 준비 중이에요.'),
                        onNotificationTap: () =>
                            _showHomeSnackBar(context, '알림은 준비 중이에요.'),
                      ),
                      const SizedBox(height: 18),
                      _TodaySchedulePanel(
                        tripInfo: tripInfo,
                        schedules: schedules,
                        onFreeTap: () => showFreeTimeRecommendSheet(context),
                      ),
                      const SizedBox(height: 16),
                      _QuickActionGrid(
                        onRouteTap: () => context.go('/plan'),
                        onFreeTap: () => showFreeTimeRecommendSheet(context),
                        onExploreTap: () => context.go('/explore'),
                      ),
                      const SizedBox(height: 16),
                      _AiRecommendationCard(
                        onTap: () => showFreeTimeRecommendSheet(context),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _HomeHeader extends StatelessWidget {
  const _HomeHeader({
    required this.tripInfo,
    required this.onMenuTap,
    required this.onNotificationTap,
  });

  final TripInfo tripInfo;
  final VoidCallback onMenuTap;
  final VoidCallback onNotificationTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            _HeaderIconButton(icon: Icons.menu, onTap: onMenuTap),
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
              icon: Icons.notifications_none_rounded,
              onTap: onNotificationTap,
            ),
          ],
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.92),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: ChiwawaColors.border),
            boxShadow: const [
              BoxShadow(
                color: Color(0x12E45F78),
                blurRadius: 22,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: Row(
            children: [
              const MascotAvatar(),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '복잡한 건 치와 두고 일단 와',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      '${tripInfo.tripName} · ${tripInfo.weather}',
                      style: const TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _HeaderIconButton extends StatelessWidget {
  const _HeaderIconButton({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: SizedBox(
        width: 44,
        height: 44,
        child: Icon(icon, color: ChiwawaColors.textPrimary, size: 24),
      ),
    );
  }
}

class _TodaySchedulePanel extends StatelessWidget {
  const _TodaySchedulePanel({
    required this.tripInfo,
    required this.schedules,
    required this.onFreeTap,
  });

  final TripInfo tripInfo;
  final List<ScheduleItem> schedules;
  final VoidCallback onFreeTap;

  @override
  Widget build(BuildContext context) {
    final visibleSchedules =
        schedules.where((schedule) => schedule.place != null).take(4).toList();

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 12, 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: ChiwawaColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x10E45F78),
            blurRadius: 24,
            offset: Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  '오늘의 일정',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: ChiwawaColors.secondary,
                  borderRadius: BorderRadius.circular(99),
                ),
                child: Text(
                  tripInfo.currentDay,
                  style: const TextStyle(
                    color: ChiwawaColors.primary,
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          for (var index = 0; index < visibleSchedules.length; index++)
            _ScheduleSummaryRow(
              schedule: visibleSchedules[index],
              isLast: index == visibleSchedules.length - 1,
              imageSeed: index + 21,
              onTap: visibleSchedules[index].status == ScheduleStatus.free
                  ? onFreeTap
                  : null,
            ),
        ],
      ),
    );
  }
}

class _ScheduleSummaryRow extends StatelessWidget {
  const _ScheduleSummaryRow({
    required this.schedule,
    required this.isLast,
    required this.imageSeed,
    this.onTap,
  });

  final ScheduleItem schedule;
  final bool isLast;
  final int imageSeed;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: Padding(
        padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 44,
              child: Padding(
                padding: const EdgeInsets.only(top: 11),
                child: Text(
                  schedule.time,
                  style: const TextStyle(
                    color: ChiwawaColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
            _SchedulePin(isLast: isLast),
            const SizedBox(width: 10),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(
                  schedule.place ?? '빈 시간 추천',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            _PlaceThumbnail(seed: imageSeed, label: schedule.place ?? ''),
          ],
        ),
      ),
    );
  }
}

class _SchedulePin extends StatelessWidget {
  const _SchedulePin({required this.isLast});

  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 18,
      height: 62,
      child: Stack(
        alignment: Alignment.topCenter,
        children: [
          if (!isLast)
            Positioned(
              top: 23,
              bottom: -4,
              child: Container(width: 1.4, color: ChiwawaColors.border),
            ),
          const Positioned(
            top: 9,
            child: Icon(
              Icons.location_on_rounded,
              color: ChiwawaColors.primary,
              size: 18,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlaceThumbnail extends StatelessWidget {
  const _PlaceThumbnail({required this.seed, required this.label});

  final int seed;
  final String label;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: SizedBox(
        width: 72,
        height: 54,
        child: Image.asset(
          MockImages.placeThumbnail(seed),
          fit: BoxFit.cover,
          errorBuilder: (context, error, stackTrace) =>
              _ThumbnailFallback(label: label),
        ),
      ),
    );
  }
}

void _showHomeSnackBar(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));
}

class _ThumbnailFallback extends StatelessWidget {
  const _ThumbnailFallback({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final icon = label.contains('스카이')
        ? Icons.cell_tower_rounded
        : label.contains('신주쿠')
            ? Icons.nightlife_rounded
            : label.contains('시부야')
                ? Icons.apartment_rounded
                : Icons.temple_buddhist_rounded;

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFFFDCE4), Color(0xFFFFF4F6)],
        ),
      ),
      child: Icon(icon, color: ChiwawaColors.primary, size: 28),
    );
  }
}

class _QuickActionGrid extends StatelessWidget {
  const _QuickActionGrid({
    required this.onRouteTap,
    required this.onFreeTap,
    required this.onExploreTap,
  });

  final VoidCallback onRouteTap;
  final VoidCallback onFreeTap;
  final VoidCallback onExploreTap;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _QuickActionCard(
            icon: Icons.route_rounded,
            label: '경로 최적화',
            onTap: onRouteTap,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _QuickActionCard(
            icon: Icons.schedule_rounded,
            label: '빈 시간 추천',
            onTap: onFreeTap,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _QuickActionCard(
            icon: Icons.search_rounded,
            label: '주변 탐색',
            onTap: onExploreTap,
          ),
        ),
      ],
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  const _QuickActionCard({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        height: 92,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: ChiwawaColors.border),
          boxShadow: const [
            BoxShadow(
              color: Color(0x0DE45F78),
              blurRadius: 16,
              offset: Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: ChiwawaColors.primary, size: 28),
            const SizedBox(height: 8),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                label,
                maxLines: 1,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AiRecommendationCard extends StatelessWidget {
  const _AiRecommendationCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: ChiwawaColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x10E45F78),
            blurRadius: 22,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'AI 추천',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  '지금 주변에서 가볼 만한 곳은 어디일까요?',
                  style: TextStyle(
                    fontSize: 13,
                    height: 1.35,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 12),
                FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: ChiwawaColors.primary,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(92, 34),
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    textStyle: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  onPressed: onTap,
                  child: const Text('추천 보기'),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          const _RecommendationIllustration(),
        ],
      ),
    );
  }
}

class _RecommendationIllustration extends StatelessWidget {
  const _RecommendationIllustration();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 92,
      height: 92,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFFFFDDE6), Color(0xFFE6F4F0)],
        ),
      ),
      child: Stack(
        children: [
          const Positioned(
            left: 10,
            top: 14,
            child: Icon(
              Icons.cloud_rounded,
              color: Colors.white,
              size: 32,
            ),
          ),
          Positioned(
            right: 9,
            top: 10,
            child: Container(
              width: 20,
              height: 20,
              decoration: const BoxDecoration(
                color: Color(0xFFFFF6A5),
                shape: BoxShape.circle,
              ),
            ),
          ),
          const Positioned(
            left: 16,
            bottom: 16,
            child: Icon(
              Icons.cottage_rounded,
              color: ChiwawaColors.primary,
              size: 46,
            ),
          ),
          const Positioned(
            right: 10,
            bottom: 12,
            child: Icon(
              Icons.local_florist_rounded,
              color: Colors.white,
              size: 26,
            ),
          ),
        ],
      ),
    );
  }
}
