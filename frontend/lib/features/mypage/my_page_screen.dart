import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../shared/widgets/app_viewport.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/providers/data_providers.dart';
import '../../shared/widgets/mascot_avatar.dart';

class MyPageScreen extends ConsumerWidget {
  const MyPageScreen({super.key});

  static const _travelItems = [
    _MyPageItem(
      title: '현재 여행 일정',
      description: '오늘 일정과 빈 시간 추천을 확인해요.',
      icon: Icons.calendar_month_rounded,
      route: '/home',
    ),
    _MyPageItem(
      title: 'AI 일정 설계',
      description: '가고 싶은 장소를 넣고 동선을 정리해요.',
      icon: Icons.auto_awesome_rounded,
      route: '/plan',
    ),
    _MyPageItem(
      title: '사진으로 장소 찾기',
      description: '사진 속 여행지를 찾고 길찾기로 이어가요.',
      icon: Icons.camera_alt_rounded,
      route: '/explore',
    ),
    _MyPageItem(
      title: '여행 기록',
      description: '사진과 이동 동선으로 여행을 정리해요.',
      icon: Icons.photo_album_rounded,
      route: '/memorial',
    ),
  ];

  static const _helpItems = [
    _MyPageItem(
      title: '문의하기',
      description: '서비스 이용 중 궁금한 점을 남겨요.',
      icon: Icons.support_agent_rounded,
    ),
    _MyPageItem(
      title: '이용 가이드',
      description: '치와와 기능을 빠르게 살펴봐요.',
      icon: Icons.menu_book_rounded,
    ),
    _MyPageItem(
      title: '개인정보 및 위치 정보 안내',
      description: '사진과 위치 정보 사용 방식을 확인해요.',
      icon: Icons.privacy_tip_rounded,
    ),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final tripInfo = ref.watch(tripInfoProvider).valueOrNull;
    final settingItems = [
      _MyPageItem(
        title: '계정 연결',
        description: auth.isSignedIn
            ? '${auth.user?.email ?? '구글 계정'} 연결됨'
            : '로그인 없이 둘러보는 중 · 구글 계정을 연결해 보세요',
        icon: Icons.account_circle_rounded,
        route: auth.isSignedIn ? null : '/auth',
        onTap: auth.isSignedIn
            ? () => _showComingSoonSnackBar(context, '계정 관리')
            : null,
      ),
      if (auth.isSignedIn)
        _MyPageItem(
          title: '로그아웃',
          description: '이 기기에서 구글 계정 연결을 해제해요.',
          icon: Icons.logout_rounded,
          onTap: () => ref.read(authControllerProvider.notifier).signOut(),
        ),
      const _MyPageItem(
        title: '알림 설정',
        description: '일정 변경과 추천 알림',
        icon: Icons.notifications_rounded,
      ),
      const _MyPageItem(
        title: '언어 및 지역',
        description: '한국어 · 일본 여행',
        icon: Icons.language_rounded,
      ),
      const _MyPageItem(
        title: '앱 정보',
        description: 'App + Web prototype',
        icon: Icons.info_rounded,
      ),
    ];

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
                  constraints.maxWidth > AppLayout.maxContentWidth
                      ? AppLayout.maxContentWidth
                      : constraints.maxWidth;

              return Align(
                alignment: Alignment.topCenter,
                child: SizedBox(
                  width: contentWidth,
                  height: constraints.maxHeight,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
                    children: [
                      _ProfileCard(
                          tripName: tripInfo?.tripName ?? '여행 준비 중',
                          currentDay: tripInfo?.currentDay ?? ''),
                      const SizedBox(height: 22),
                      const _SectionTitle(title: '내 여행 관리'),
                      const SizedBox(height: 10),
                      const _SettingsGroup(items: _travelItems),
                      const SizedBox(height: 22),
                      const _SectionTitle(title: '계정 및 앱 설정'),
                      const SizedBox(height: 10),
                      _SettingsGroup(items: settingItems),
                      const SizedBox(height: 22),
                      const _SectionTitle(title: '도움말'),
                      const SizedBox(height: 10),
                      const _SettingsGroup(items: _helpItems),
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

class _ProfileCard extends ConsumerWidget {
  const _ProfileCard({
    required this.tripName,
    required this.currentDay,
  });

  final String tripName;
  final String currentDay;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.95),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: ChiwawaColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x12E45F78),
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
              const MascotAvatar(size: 58),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      auth.user?.displayName ?? '치와와 여행자',
                      style: const TextStyle(
                        color: ChiwawaColors.textPrimary,
                        fontSize: 21,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      '$tripName · $currentDay',
                      style: const TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Text(
            'AI 여행 플래너 서비스',
            style: TextStyle(
              color: ChiwawaColors.primary,
              fontSize: 13,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            '여행 준비부터 기록까지 치와와와 함께 관리해요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 13,
              height: 1.35,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: ChiwawaColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
                textStyle: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w900,
                ),
              ),
              onPressed: () => _showComingSoonSnackBar(context, '프로필 관리'),
              icon: const Icon(Icons.edit_rounded, size: 18),
              label: const Text('프로필 관리'),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
    );
  }
}

class _SettingsGroup extends StatelessWidget {
  const _SettingsGroup({required this.items});

  final List<_MyPageItem> items;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
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
        children: [
          for (var index = 0; index < items.length; index++) ...[
            _SettingsRow(item: items[index]),
            if (index != items.length - 1) const Divider(height: 1, indent: 72),
          ],
        ],
      ),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({required this.item});

  final _MyPageItem item;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: () {
        final customTap = item.onTap;
        if (customTap != null) {
          customTap();
          return;
        }
        final route = item.route;
        if (route == null) {
          _showComingSoonSnackBar(context, item.title);
          return;
        }
        context.go(route);
      },
      child: Padding(
        padding: const EdgeInsets.fromLTRB(15, 13, 12, 13),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: ChiwawaColors.secondary,
                borderRadius: BorderRadius.circular(15),
              ),
              child: Icon(item.icon, color: ChiwawaColors.primary, size: 25),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    item.description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: ChiwawaColors.textSecondary,
                      fontSize: 12,
                      height: 1.3,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Icon(
              Icons.chevron_right_rounded,
              color: ChiwawaColors.textMuted,
            ),
          ],
        ),
      ),
    );
  }
}

class _MyPageItem {
  const _MyPageItem({
    required this.title,
    required this.description,
    required this.icon,
    this.route,
    this.onTap,
  });

  final String title;
  final String description;
  final IconData icon;
  final String? route;
  final VoidCallback? onTap;
}

void _showComingSoonSnackBar(BuildContext context, String label) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(content: Text('$label은 준비 중이에요.')),
    );
}
