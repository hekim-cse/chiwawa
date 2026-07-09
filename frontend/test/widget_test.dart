import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:chiwawa/core/confirmed_route.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/plan_repository.dart';
import 'package:chiwawa/core/saved_photo_places.dart';
import 'package:chiwawa/features/explore/explore_screen.dart';
import 'package:chiwawa/features/plan/plan_screen.dart';
import 'package:chiwawa/main.dart';

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
  void useMobileTestSurface(WidgetTester tester) {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets('chiwawa app opens the home screen', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    expect(find.text('치와와'), findsOneWidget);
    expect(find.textContaining('도쿄 봄 여행'), findsOneWidget);
    expect(find.text('복잡한 건 치와 두고 일단 와'), findsOneWidget);
    expect(find.bySemanticsLabel('치와와 마스코트'), findsOneWidget);
    expect(find.text('오늘의 일정'), findsOneWidget);
    expect(find.text('홈'), findsWidgets);
    expect(find.text('일정'), findsOneWidget);
  });

  testWidgets('chiwawa app opens the account settings my page', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

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
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('AI 일정 설계'));
    await tester.pumpAndSettle();

    expect(find.text('AI 일정 설계'), findsOneWidget);
    expect(find.text('AI 경로 최적화'), findsOneWidget);
  });

  testWidgets('chiwawa my page account row opens auth screen', (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('계정 연결'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('계정 연결'));
    await tester.pumpAndSettle();

    expect(find.text('chiwawa'), findsOneWidget);
    expect(find.text('여행 준비를 이어서 관리해요.'), findsOneWidget);
    expect(find.text('이메일'), findsOneWidget);
    expect(find.text('비밀번호'), findsOneWidget);
    expect(find.text('로그인 없이 둘러보기'), findsOneWidget);
    expect(find.text('홈'), findsNothing);
  });

  testWidgets('chiwawa auth validates empty sign in inputs', (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('계정 연결'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('계정 연결'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, '로그인'));
    await tester.pump(const Duration(milliseconds: 250));

    expect(find.text('필수 정보를 입력해 주세요.'), findsOneWidget);
  });

  testWidgets('chiwawa auth validates mismatched sign up passwords',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('계정 연결'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('계정 연결'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('회원가입'));
    await tester.pumpAndSettle();

    await tester.enterText(
        find.byKey(const ValueKey('auth-name-field')), '왘왘 여행자');
    await tester.enterText(
      find.byKey(const ValueKey('auth-email-field')),
      'user@example.com',
    );
    await tester.enterText(
      find.byKey(const ValueKey('auth-password-field')),
      'password123',
    );
    await tester.enterText(
      find.byKey(const ValueKey('auth-confirm-password-field')),
      'different123',
    );
    await tester
        .ensureVisible(find.byKey(const ValueKey('auth-submit-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('auth-submit-button')));
    await tester.pump(const Duration(milliseconds: 600));

    expect(find.text('비밀번호가 서로 달라요.'), findsOneWidget);
  });

  testWidgets('chiwawa auth signs up with mock state', (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('계정 연결'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('계정 연결'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('회원가입'));
    await tester.pumpAndSettle();

    await tester.enterText(
        find.byKey(const ValueKey('auth-name-field')), '왘왘 여행자');
    await tester.enterText(
      find.byKey(const ValueKey('auth-email-field')),
      'user@example.com',
    );
    await tester.enterText(
      find.byKey(const ValueKey('auth-password-field')),
      'password123',
    );
    await tester.enterText(
      find.byKey(const ValueKey('auth-confirm-password-field')),
      'password123',
    );
    await tester
        .ensureVisible(find.byKey(const ValueKey('auth-submit-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('auth-submit-button')));
    await tester.pumpAndSettle();

    expect(find.text('왘왘 여행자'), findsOneWidget);

    await tester.ensureVisible(find.text('계정 연결'));
    await tester.pumpAndSettle();

    expect(find.text('user@example.com 연결됨'), findsOneWidget);
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

    await tester.tap(find.byKey(const ValueKey('select-saved-place-아사쿠사 센소지')));
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
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

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
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();

    await tester
        .ensureVisible(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pump(const Duration(milliseconds: 1200));

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    container
        .read(confirmedRouteProvider.notifier)
        .confirm(container.read(routeOptimizationProvider).places);
    await tester.pump();

    await tester.tap(find.text('기록'));
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
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();

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
