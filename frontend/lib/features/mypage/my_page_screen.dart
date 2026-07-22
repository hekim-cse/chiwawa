import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/providers/data_providers.dart';
import '../../core/settings/app_settings_controller.dart';
import '../../shared/widgets/app_list_group.dart';
import '../../shared/widgets/app_section_header.dart';
import '../../shared/widgets/app_viewport.dart';
import '../../shared/widgets/mascot_avatar.dart';
import 'models/my_page_menu_item.dart';
import 'my_page_routes.dart';

const _myPageSupportingTextColor = Color(0xFF7C7074);

class MyPageScreen extends ConsumerWidget {
  const MyPageScreen({super.key});

  static const _travelItems = [
    MyPageMenuItem(
      title: '여행 목록 및 전환',
      description: '새 여행을 만들고 현재 여행을 바꿔요.',
      icon: Icons.luggage_rounded,
      route: '/trips',
    ),
    MyPageMenuItem(
      title: '현재 여행 일정',
      description: '오늘 일정과 빈 시간 추천을 확인해요.',
      icon: Icons.calendar_month_rounded,
      route: '/home',
    ),
    MyPageMenuItem(
      title: 'AI 일정 설계',
      description: '가고 싶은 장소를 넣고 동선을 정리해요.',
      icon: Icons.auto_awesome_rounded,
      route: '/plan',
    ),
    MyPageMenuItem(
      title: '사진으로 장소 찾기',
      description: '사진 속 여행지를 찾고 길찾기로 이어가요.',
      icon: Icons.camera_alt_rounded,
      route: '/explore',
    ),
    MyPageMenuItem(
      title: '여행 기록',
      description: '사진과 이동 동선으로 여행을 정리해요.',
      icon: Icons.photo_album_rounded,
      route: '/memorial',
    ),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final settings = ref.watch(appSettingsProvider);
    final tripInfo = ref.watch(tripInfoProvider).valueOrNull;
    final settingItems = [
      MyPageMenuItem(
        title: '계정 연결',
        description: auth.isSignedIn
            ? '${auth.user?.email ?? 'Google 계정'} 연결됨'
            : '로그인 없이 둘러보는 중',
        icon: Icons.account_circle_rounded,
        route: MyPageRoutes.account,
        value: auth.isSignedIn ? '연결됨' : '게스트',
      ),
      MyPageMenuItem(
        title: '알림 설정',
        description:
            settings.tripUpdatesEnabled || settings.memoryHighlightsEnabled
                ? '여행 일정과 기록 안내를 받고 있어요.'
                : '모든 안내가 꺼져 있어요.',
        icon: Icons.notifications_none_rounded,
        route: MyPageRoutes.notifications,
      ),
      const MyPageMenuItem(
        title: '언어 및 지역',
        description: '한국어 · 일본 여행 · 24시간제',
        icon: Icons.language_rounded,
        route: MyPageRoutes.languageRegion,
        value: '한국어',
      ),
      const MyPageMenuItem(
        title: '앱 정보',
        description: 'chiwawa 1.0.0 · App + Web',
        icon: Icons.info_rounded,
        route: MyPageRoutes.appInfo,
        value: '1.0.0',
      ),
    ];
    const helpItems = [
      MyPageMenuItem(
        title: '문의하기',
        description: '문의 유형과 내용을 작성해 이메일로 보내요.',
        icon: Icons.support_agent_rounded,
        route: MyPageRoutes.support,
      ),
      MyPageMenuItem(
        title: '이용 가이드',
        description: '사진부터 여행 기록까지 흐름을 살펴봐요.',
        icon: Icons.menu_book_rounded,
        route: MyPageRoutes.guide,
      ),
      MyPageMenuItem(
        title: '개인정보 및 위치 정보 안내',
        description: '사진과 위치 정보가 쓰이는 범위를 확인해요.',
        icon: Icons.privacy_tip_rounded,
        route: MyPageRoutes.privacy,
      ),
    ];

    return SafeArea(
      child: ColoredBox(
        color: ChiwawaColors.background,
        child: ListView(
          padding: AppLayout.pageInsets(context, top: 16, bottom: 32),
          children: [
            _ProfileCard(
              tripName: tripInfo?.tripName ?? '여행 준비 중',
              currentDay: tripInfo?.currentDay ?? '',
            ),
            const SizedBox(height: ChiwawaSpacing.section),
            const AppSectionHeader(title: '내 여행 관리'),
            const SizedBox(height: ChiwawaSpacing.sm),
            const _MenuGroup(items: _travelItems),
            const SizedBox(height: ChiwawaSpacing.section),
            const AppSectionHeader(title: '계정 및 앱 설정'),
            const SizedBox(height: ChiwawaSpacing.sm),
            _MenuGroup(items: settingItems),
            const SizedBox(height: ChiwawaSpacing.section),
            const AppSectionHeader(title: '도움말'),
            const SizedBox(height: ChiwawaSpacing.sm),
            const _MenuGroup(items: helpItems),
          ],
        ),
      ),
    );
  }
}

class _ProfileCard extends ConsumerWidget {
  const _ProfileCard({required this.tripName, required this.currentDay});

  final String tripName;
  final String currentDay;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const MascotAvatar(size: 58),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      auth.user?.displayName ?? '치와와 여행자',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 5),
                    Text(
                      [tripName, currentDay]
                          .where((value) => value.isNotEmpty)
                          .join(' · '),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: _myPageSupportingTextColor,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: ChiwawaSpacing.sm),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              key: const ValueKey('open-profile-settings'),
              style: TextButton.styleFrom(
                foregroundColor: ChiwawaColors.primary,
                padding: const EdgeInsets.symmetric(horizontal: 4),
              ),
              onPressed: () => context.push(MyPageRoutes.profile),
              icon: const Icon(Icons.edit_rounded, size: 18),
              label: const Text('프로필 관리'),
            ),
          ),
        ],
      ),
    );
  }
}

class _MenuGroup extends StatelessWidget {
  const _MenuGroup({required this.items});

  final List<MyPageMenuItem> items;

  @override
  Widget build(BuildContext context) {
    return AppListGroup(
      children: [
        for (var index = 0; index < items.length; index++)
          AppListRow(
            key: ValueKey('mypage-menu-${items[index].route}'),
            title: items[index].title,
            titleColor: ChiwawaColors.primary,
            subtitle: items[index].description,
            subtitleColor: _myPageSupportingTextColor,
            leading: AppLeadingIcon(icon: items[index].icon),
            trailing: _MenuTrailing(value: items[index].value),
            showDivider: index != items.length - 1,
            onTap: () => _openRoute(context, items[index].route),
          ),
      ],
    );
  }

  void _openRoute(BuildContext context, String route) {
    if (route.startsWith('${MyPageRoutes.overview}/')) {
      context.push(route);
    } else {
      context.go(route);
    }
  }
}

class _MenuTrailing extends StatelessWidget {
  const _MenuTrailing({this.value});

  final String? value;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (value != null) ...[
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 72),
            child: Text(
              value!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.right,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: _myPageSupportingTextColor,
                  ),
            ),
          ),
          const SizedBox(width: ChiwawaSpacing.xxs),
        ],
        const Icon(
          Icons.chevron_right_rounded,
          color: ChiwawaColors.textMuted,
        ),
      ],
    );
  }
}
