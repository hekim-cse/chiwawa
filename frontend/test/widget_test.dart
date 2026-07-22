import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:chiwawa/core/confirmed_route.dart';
import 'package:chiwawa/core/auth/auth_controller.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/plan_repository.dart';
import 'package:chiwawa/core/saved_photo_places.dart';
import 'package:chiwawa/features/auth/auth_screen.dart';
import 'package:chiwawa/features/explore/explore_screen.dart';
import 'package:chiwawa/features/plan/plan_screen.dart';
import 'package:chiwawa/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _FailingPlanRepository implements PlanRepository {
  @override
  List<String> get defaultSelectedPlaces => const ['아사쿠사 센소지', '도쿄 타워'];

  @override
  Future<List<RoutePlace>> optimizeRoute(
    List<String> places,
    TravelPreference preference,
  ) async {
    throw StateError('mock failure');
  }
}

void main() {
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  void useMobileTestSurface(WidgetTester tester) {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  // 앱은 로그인 화면으로 시작하므로, 홈 플로우 테스트는 게스트로 입장한다
  Future<void> pumpAppAsGuest(WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();
  }

  testWidgets('chiwawa app opens the home screen', (tester) async {
    await pumpAppAsGuest(tester);

    expect(find.text('치와와'), findsOneWidget);
    expect(find.textContaining('도쿄 봄 여행'), findsOneWidget);
    expect(find.text('복잡한 건 치와 두고 일단 와'), findsOneWidget);
    expect(find.bySemanticsLabel('치와와 마스코트'), findsOneWidget);
    expect(find.text('오늘의 일정'), findsOneWidget);
    expect(find.text('홈'), findsWidgets);
    expect(find.text('일정'), findsOneWidget);
  });

  testWidgets('chiwawa app opens the account settings my page', (tester) async {
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    expect(find.text('마이페이지\n추후 구현 예정'), findsNothing);
    expect(find.text('전체 서비스 흐름'), findsNothing);
    expect(find.text('치와와 여행자'), findsOneWidget);

    await tester.scrollUntilVisible(find.text('계정 및 앱 설정'), 300);
    await tester.pumpAndSettle();

    expect(find.text('계정 및 앱 설정'), findsOneWidget);
    expect(find.text('알림 설정'), findsOneWidget);
    expect(find.text('언어 및 지역'), findsOneWidget);

    await tester.scrollUntilVisible(find.text('도움말'), 300);
    await tester.pumpAndSettle();

    expect(find.text('도움말'), findsOneWidget);
  });

  testWidgets('chiwawa my page route row opens plan screen', (tester) async {
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('AI 일정 설계'));
    await tester.pumpAndSettle();

    expect(find.byType(PlanScreen), findsOneWidget);
    expect(find.text('AI 일정 설계'), findsOneWidget);
  });

  testWidgets('chiwawa my page account row opens auth screen', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('계정 연결'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('계정 연결'));
    await tester.pumpAndSettle();

    expect(find.text('Google로 시작하기'), findsOneWidget);
    expect(find.text('로그인 없이 둘러보기'), findsOneWidget);
    expect(find.text('AI와 함께하는 일본 여행 플래너'), findsOneWidget);
    expect(find.text('오늘의 일정'), findsNothing);
  });

  testWidgets('auth gate blocks app until choice is made', (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    expect(find.text('Google로 시작하기'), findsOneWidget);
    expect(find.text('로그인 없이 둘러보기'), findsOneWidget);
    expect(find.text('오늘의 일정'), findsNothing);
  });

  testWidgets('mock google sign in enters home with account connected',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Google로 시작하기'));
    await tester.pumpAndSettle();

    expect(find.text('오늘의 일정'), findsOneWidget);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    expect(find.text('치와와 여행자'), findsOneWidget);

    await tester.ensureVisible(find.text('계정 연결'));
    await tester.pumpAndSettle();

    expect(find.text('traveler@chiwawa.app 연결됨'), findsOneWidget);
    expect(find.text('로그아웃'), findsOneWidget);
  });

  testWidgets('auth route exchanges OAuth code and enters home',
      (tester) async {
    useMobileTestSurface(tester);
    SharedPreferences.setMockInitialValues({});

    final router = GoRouter(
      initialLocation: '/auth?code=web-code&state=csrf-state',
      routes: [
        GoRoute(
          path: '/auth',
          builder: (context, state) => AuthScreen(
            oauthCode: state.uri.queryParameters['code'],
            oauthState: state.uri.queryParameters['state'],
          ),
        ),
        GoRoute(
          path: '/home',
          builder: (context, state) => const Scaffold(
            body: Text('홈 도착'),
          ),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(child: MaterialApp.router(routerConfig: router)),
    );
    await tester.pumpAndSettle();

    expect(find.text('홈 도착'), findsOneWidget);

    final container = ProviderScope.containerOf(
      tester.element(find.text('홈 도착')),
    );
    final auth = container.read(authControllerProvider);
    expect(auth.isSignedIn, isTrue);
    expect(auth.token, 'mock-jwt-token');
    expect(container.read(authTokenProvider), 'mock-jwt-token');
  });

  testWidgets('logout returns to auth screen', (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Google로 시작하기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('로그아웃'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그아웃'));
    await tester.pumpAndSettle();

    expect(find.text('Google로 시작하기'), findsOneWidget);
    expect(find.text('오늘의 일정'), findsNothing);
  });

  testWidgets('Photo search result can be saved for plan building',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreResultVisibleProvider.overrideWith((ref) => true),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('탐색'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('일정에 추가'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, '일정에 추가'));
    await tester.pump(const Duration(milliseconds: 250));

    expect(find.text('아사쿠사 센소지 일정 후보에 저장했어요.'), findsOneWidget);
    expect(find.text('일정 후보 저장됨'), findsOneWidget);

    await tester.ensureVisible(find.text('일정에 추가'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, '일정에 추가'));
    await tester.pump(const Duration(milliseconds: 250));

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(container.read(savedPhotoPlacesProvider), hasLength(1));
  });

  testWidgets('Saved photo place appears on the plan screen', (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreResultVisibleProvider.overrideWith((ref) => true),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('탐색'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('일정에 추가'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, '일정에 추가'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();

    expect(find.text('사진으로 저장한 장소'), findsOneWidget);
    expect(find.byKey(const ValueKey('select-saved-place-아사쿠사 센소지')),
        findsOneWidget);

    final savedPlace =
        find.byKey(const ValueKey('select-saved-place-아사쿠사 센소지'));
    await tester.ensureVisible(savedPlace);
    await tester.pumpAndSettle();
    await tester.tap(savedPlace);
    await tester.pump(const Duration(milliseconds: 250));

    expect(find.widgetWithText(InputChip, '아사쿠사 센소지'), findsOneWidget);
  });

  testWidgets('Saved photo place can be removed from plan saved section',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreResultVisibleProvider.overrideWith((ref) => true),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('탐색'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('일정에 추가'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, '일정에 추가'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();
    final removeSavedPlaceButton =
        find.byKey(const ValueKey('remove-saved-place-아사쿠사 센소지')).last;
    await tester.ensureVisible(removeSavedPlaceButton);
    await tester.pumpAndSettle();
    await tester.tap(removeSavedPlaceButton);
    await tester.pumpAndSettle();

    expect(find.text('아사쿠사 센소지 저장 목록에서 삭제했어요.'), findsOneWidget);
    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(container.read(savedPhotoPlacesProvider), isEmpty);
  });

  testWidgets('AI route optimization shows done state results', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();

    await tester
        .ensureVisible(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pump(const Duration(milliseconds: 1200));

    expect(find.text('최적 경로 결과'), findsOneWidget);
    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(
      container.read(routeOptimizationProvider).status,
      AiJobStatus.done,
    );
  });

  testWidgets('Confirmed optimized route appears on memorial preview',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();

    await tester
        .ensureVisible(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    container
        .read(confirmedRouteProvider.notifier)
        .confirm(container.read(routeOptimizationProvider).places);
    await tester.pump();

    await tester.tap(find.text('기록'));
    await tester.pumpAndSettle();

    await tester.dragUntilVisible(
      find.text('확정 일정 미리보기'),
      find.byKey(const ValueKey('memorial-scroll')),
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    expect(find.text('확정 일정 미리보기'), findsOneWidget);
    expect(find.text('AI 일정 설계에서 확정한 동선을 기록 흐름으로 이어봤어요.'), findsOneWidget);
    expect(find.text('메이지 신궁'), findsOneWidget);
  });

  testWidgets('AI route optimization shows failed state and retry',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          planRepositoryProvider.overrideWithValue(_FailingPlanRepository()),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();

    await tester
        .ensureVisible(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('경로 최적화에 실패했어요. 다시 시도해 주세요.'), findsOneWidget);
    expect(find.text('다시 시도'), findsOneWidget);
  });

  testWidgets('Travel preference chips store enum state', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('맛집'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('맛집'));
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(
      container.read(travelPreferenceProvider).themes,
      contains(TravelTheme.food),
    );
  });
}
