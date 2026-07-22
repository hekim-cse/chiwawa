import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/auth/auth_controller.dart';
import '../features/auth/auth_screen.dart';
import '../features/explore/explore_screen.dart';
import '../features/home/home_screen.dart';
import '../features/memorial/memorial_screen.dart';
import '../features/mypage/my_page_screen.dart';
import '../features/mypage/my_page_routes.dart';
import '../features/mypage/pages/account_settings_screen.dart';
import '../features/mypage/pages/app_info_screen.dart';
import '../features/mypage/pages/language_region_screen.dart';
import '../features/mypage/pages/notification_settings_screen.dart';
import '../features/mypage/pages/privacy_screen.dart';
import '../features/mypage/pages/profile_settings_screen.dart';
import '../features/mypage/pages/support_screen.dart';
import '../features/mypage/pages/user_guide_screen.dart';
import '../features/plan/plan_screen.dart';
import '../features/trips/trip_list_screen.dart';
import '../shared/widgets/app_viewport.dart';
import '../shared/widgets/bottom_nav_bar.dart';

final routerProvider = Provider<GoRouter>((ref) {
  // 인증 상태가 바뀌면 라우터가 redirect를 재평가하도록 연결
  final refresh = ValueNotifier(0);
  ref.listen(authControllerProvider, (_, __) => refresh.value++);
  ref.onDispose(refresh.dispose);

  return GoRouter(
    initialLocation: '/auth',
    refreshListenable: refresh,
    redirect: (context, state) {
      final status = ref.read(authControllerProvider).status;
      final location = state.matchedLocation;

      if (location == '/') {
        return status == AuthStatus.signedOut ? '/auth' : '/home';
      }
      // 로그인/둘러보기 선택 전에는 로그인 화면만 접근 가능
      if (status == AuthStatus.signedOut && location != '/auth') {
        return '/auth';
      }
      // 로그인 완료 상태에서 로그인 화면 접근 시 홈으로 (딥링크 복귀 포함)
      if (status == AuthStatus.signedIn && location == '/auth') {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/auth',
        pageBuilder: (context, state) => NoTransitionPage(
          child: AuthScreen(
            oauthCode: state.uri.queryParameters['code'],
            oauthState: state.uri.queryParameters['state'],
          ),
        ),
      ),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: '/home',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: HomeScreen()),
          ),
          GoRoute(
            path: '/plan',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: PlanScreen()),
          ),
          GoRoute(
            path: '/explore',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: ExploreScreen()),
          ),
          GoRoute(
            path: '/memorial',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: MemorialScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.overview,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: MyPageScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.profile,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: ProfileSettingsScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.account,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: AccountSettingsScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.notifications,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: NotificationSettingsScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.languageRegion,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: LanguageRegionScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.appInfo,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: AppInfoScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.support,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: SupportScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.guide,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: UserGuideScreen()),
          ),
          GoRoute(
            path: MyPageRoutes.privacy,
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: PrivacyScreen()),
          ),
          GoRoute(
            path: '/trips',
            pageBuilder: (context, state) =>
                const NoTransitionPage(child: TripListScreen()),
          ),
        ],
      ),
    ],
  );
});

class AppShell extends StatelessWidget {
  const AppShell({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AppViewport(child: child),
      bottomNavigationBar: const BottomNavBar(),
    );
  }
}
