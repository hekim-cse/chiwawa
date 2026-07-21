import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/models/travel_models.dart';
import '../../core/providers/data_providers.dart';
import '../../shared/widgets/app_viewport.dart';
import '../../shared/widgets/async_value_view.dart';
import '../../shared/widgets/app_section_header.dart';
import '../assist/widgets/free_time_sheet.dart';
import 'widgets/home_header.dart';
import 'widgets/home_menu_sheet.dart';
import 'widgets/home_quick_actions.dart';
import 'widgets/home_recommendation_card.dart';
import 'widgets/today_schedule_panel.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AsyncValueView<HomeData>(
      value: ref.watch(homeDataProvider),
      onRetry: () => ref.invalidate(homeDataProvider),
      builder: (data) => SafeArea(
        child: ColoredBox(
          color: ChiwawaColors.background,
          child: ListView(
            padding: AppLayout.pageInsets(context, top: 12, bottom: 28),
            children: [
              HomeHeader(
                tripInfo: data.tripInfo,
                onMenuTap: () => showHomeMenuSheet(context),
                onTripTap: () => context.go('/trips'),
              ),
              const SizedBox(height: ChiwawaSpacing.section),
              AppSectionHeader(
                title: '오늘의 일정',
                description: data.tripInfo.currentDay.trim().isEmpty
                    ? null
                    : data.tripInfo.currentDay,
                trailing: TextButton(
                  onPressed: () => context.go('/plan'),
                  child: const Text('전체 보기'),
                ),
              ),
              const SizedBox(height: ChiwawaSpacing.sm),
              TodaySchedulePanel(
                tripInfo: data.tripInfo,
                schedules: data.schedules,
                onFreeTap: () => showFreeTimeRecommendSheet(context),
              ),
              const SizedBox(height: ChiwawaSpacing.lg),
              const AppSectionHeader(title: '빠른 실행'),
              const SizedBox(height: ChiwawaSpacing.sm),
              HomeQuickActions(
                actions: [
                  HomeQuickActionData(
                    id: 'route',
                    icon: Icons.route_rounded,
                    label: '경로 최적화',
                    onTap: () => context.go('/plan'),
                  ),
                  HomeQuickActionData(
                    id: 'free-time',
                    icon: Icons.schedule_rounded,
                    label: '빈 시간 추천',
                    onTap: () => showFreeTimeRecommendSheet(context),
                  ),
                  HomeQuickActionData(
                    id: 'explore',
                    icon: Icons.search_rounded,
                    label: '주변 탐색',
                    onTap: () => context.go('/explore'),
                  ),
                ],
              ),
              if (data.schedules.any(
                (schedule) => schedule.status == ScheduleStatus.free,
              )) ...[
                const SizedBox(height: ChiwawaSpacing.lg),
                HomeRecommendationCard(
                  onTap: () => showFreeTimeRecommendSheet(context),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
