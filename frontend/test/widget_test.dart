import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:chiwawa/core/confirmed_route.dart';
import 'package:chiwawa/core/auth/auth_controller.dart';
import 'package:chiwawa/core/models/place_search_models.dart';
import 'package:chiwawa/core/models/route_planning_models.dart';
import 'package:chiwawa/core/models/transport_mode.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/plan_repository.dart';
import 'package:chiwawa/core/saved_photo_places.dart';
import 'package:chiwawa/features/auth/auth_screen.dart';
import 'package:chiwawa/features/explore/explore_screen.dart';
import 'package:chiwawa/features/plan/plan_screen.dart';
import 'package:chiwawa/features/plan/models/plan_itinerary.dart';
import 'package:chiwawa/features/plan/widgets/route_map_overview.dart';
import 'package:chiwawa/main.dart';
import 'package:chiwawa/shared/widgets/adaptive_segmented_control.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _FailingPlanRepository implements PlanRepository {
  @override
  Future<List<ConfirmedRoutePlan>> fetchConfirmedRoutes() async => const [];

  @override
  List<String> get defaultSelectedPlaces => const ['아사쿠사 센소지', '도쿄 타워'];

  @override
  Future<void> confirmRoute(RouteOptimizationResult result) async {}

  @override
  Future<RouteOptimizationResult> optimizeRoute(
    RouteOptimizationRequest request,
  ) async {
    throw StateError('mock failure');
  }

  @override
  Future<WantedPlaceRecord> saveWantedPlace(
    PlanRoutePlaceInput place,
  ) async =>
      WantedPlaceRecord(id: 'server-${place.localId}', name: place.name);
}

class _ControlledPlanRepository implements PlanRepository {
  @override
  Future<List<ConfirmedRoutePlan>> fetchConfirmedRoutes() async => const [];

  final completer = Completer<RouteOptimizationResult>();

  @override
  List<String> get defaultSelectedPlaces => const ['첫 장소', '두 번째 장소'];

  @override
  Future<void> confirmRoute(RouteOptimizationResult result) async {}

  @override
  Future<RouteOptimizationResult> optimizeRoute(
    RouteOptimizationRequest request,
  ) {
    return completer.future;
  }

  @override
  Future<WantedPlaceRecord> saveWantedPlace(
    PlanRoutePlaceInput place,
  ) async =>
      WantedPlaceRecord(id: 'server-${place.localId}', name: place.name);
}

class _ConfirmedPlanRepository implements PlanRepository {
  const _ConfirmedPlanRepository();

  static const timeline = RouteTimeline(
    dayIndex: 1,
    travelMode: TransportMode.transit,
    plannedStartAt: '2026-08-01T09:00:00+02:00',
    plannedEndAt: '2026-08-01T20:00:00+02:00',
    actualEndAt: '2026-08-01T13:30:00+02:00',
    totalTravelMinutes: 90,
    totalStayMinutes: 180,
    timelineStops: [
      RouteTimelineStop(
        stopType: 'START',
        placeId: 'google-test-start',
        name: '도쿄역',
        arrivalAt: '2026-08-01T09:00:00+02:00',
        departureAt: '2026-08-01T09:00:00+02:00',
        stayMinutes: 0,
      ),
      RouteTimelineStop(
        stopType: 'POI',
        placeId: 'wanted-louvre',
        name: '루브르 박물관',
        arrivalAt: '2026-08-01T09:30:00+02:00',
        departureAt: '2026-08-01T12:30:00+02:00',
        stayMinutes: 180,
      ),
      RouteTimelineStop(
        stopType: 'END',
        placeId: 'google-test-end',
        name: '신주쿠 호텔',
        arrivalAt: '2026-08-01T13:30:00+02:00',
        departureAt: '2026-08-01T13:30:00+02:00',
        stayMinutes: 0,
      ),
    ],
  );

  @override
  List<String> get defaultSelectedPlaces => const [];

  @override
  Future<void> confirmRoute(RouteOptimizationResult result) async {}

  @override
  Future<List<ConfirmedRoutePlan>> fetchConfirmedRoutes() async => const [
        ConfirmedRoutePlan(
          dayIndex: 1,
          startPlace: _testStartPlace,
          endPlace: _testEndPlace,
          result: RouteOptimizationResult.success(
            places: [
              RoutePlace(
                placeId: 'wanted-louvre',
                name: '루브르 박물관',
                duration: '180분',
                transport: '대중교통 30분',
                category: '박물관',
              ),
            ],
            timeline: timeline,
          ),
        ),
      ];

  @override
  Future<RouteOptimizationResult> optimizeRoute(
    RouteOptimizationRequest request,
  ) async =>
      (await fetchConfirmedRoutes()).single.result;

  @override
  Future<WantedPlaceRecord> saveWantedPlace(PlanRoutePlaceInput place) async {
    return WantedPlaceRecord(id: place.localId, name: place.name);
  }
}

const _testStartPlace = PlaceSearchCandidate(
  providerPlaceId: 'google-test-start',
  name: '도쿄역',
  formattedAddress: '도쿄도 지요다구',
  latitude: 35.6812,
  longitude: 139.7671,
);

const _testEndPlace = PlaceSearchCandidate(
  providerPlaceId: 'google-test-end',
  name: '신주쿠 호텔',
  formattedAddress: '도쿄도 신주쿠구',
  latitude: 35.6896,
  longitude: 139.6917,
);

const _testPhotoResult = PhotoSearchResult(
  id: 'place-sensoji',
  searchId: 'search-sensoji',
  name: '아사쿠사 센소지',
  address: '도쿄 다이토구 아사쿠사 2-3-1',
  category: '사찰',
  latitude: 35.7148,
  longitude: 139.7967,
  confidence: 0.92,
);

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

  void useNarrowTestSurface(WidgetTester tester) {
    tester.view.physicalSize = const Size(320, 700);
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

  Future<void> selectPlanEndpoints(
    WidgetTester tester, {
    int day = 1,
  }) async {
    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    final controller = container.read(planDayConstraintsProvider.notifier);
    controller.selectStartPlace(day, _testStartPlace);
    controller.selectEndPlace(day, _testEndPlace);
    await tester.pump();
  }

  testWidgets('chiwawa app opens the home screen', (tester) async {
    await pumpAppAsGuest(tester);

    expect(find.text('치와와'), findsOneWidget);
    expect(find.textContaining('도쿄 봄 여행'), findsOneWidget);
    expect(find.text('복잡한 건 치와 두고 일단 와'), findsOneWidget);
    expect(find.bySemanticsLabel('치와와 마스코트'), findsOneWidget);
    expect(find.text('여행 일정'), findsOneWidget);
    expect(find.byKey(const ValueKey('home-next-schedule')), findsOneWidget);
    expect(find.text('홈'), findsWidgets);
    expect(find.text('일정'), findsOneWidget);
  });

  testWidgets('round-trip map renders the same endpoint as one marker',
      (tester) async {
    const hotel = RoutePlace(
      placeId: 'google-hotel',
      name: '파리 호텔',
      duration: '',
      transport: '',
      category: '',
    );
    const poi = RoutePlace(
      placeId: 'google-louvre',
      name: '루브르 박물관',
      duration: '60분',
      transport: '자동차 20분',
      category: '박물관',
    );
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: RouteMapOverview(
            stops: [
              PlanItineraryStop(
                id: 'start',
                startTime: '09:00',
                stopType: 'START',
                place: hotel,
              ),
              PlanItineraryStop(
                id: 'poi',
                startTime: '10:00',
                place: poi,
              ),
              PlanItineraryStop(
                id: 'end',
                startTime: '12:00',
                stopType: 'END',
                place: hotel,
              ),
            ],
          ),
        ),
      ),
    );

    expect(find.text('S/E'), findsOneWidget);
    expect(
        find.byKey(const ValueKey('route-map-marker-start')), findsOneWidget);
    expect(find.byKey(const ValueKey('route-map-marker-end')), findsNothing);
  });

  testWidgets('confirmed route appears on home and is restored by full view',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          planRepositoryProvider.overrideWithValue(
            const _ConfirmedPlanRepository(),
          ),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();

    expect(find.text('출발 · 도쿄역'), findsOneWidget);
    expect(find.text('루브르 박물관'), findsOneWidget);
    expect(find.text('도착 · 신주쿠 호텔'), findsOneWidget);

    await tester.tap(find.text('전체 보기'));
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(container.read(routeOptimizationProvider).status, AiJobStatus.done);
    expect(
      container.read(planDayConstraintsProvider).forDay(1).startPlace,
      _testStartPlace,
    );
    expect(
      container.read(planDayConstraintsProvider).forDay(1).endPlace,
      _testEndPlace,
    );
    expect(
      container.read(planItineraryProvider).currentStops,
      hasLength(3),
    );
    expect(find.text('도쿄역'), findsWidgets);
    expect(find.text('신주쿠 호텔'), findsWidgets);
  });

  testWidgets('home timeline keeps free time entry actionable', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    expect(find.text('빈 시간 추천'), findsNWidgets(2));
    await tester.tap(find.text('빈 시간 추천').first);
    await tester.pumpAndSettle();

    expect(find.text('일정 사이에 들를 수 있는 장소예요'), findsOneWidget);
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

  testWidgets('profile name can be edited from my page', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('프로필 관리'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const ValueKey('profile-name-field')),
      '도쿄 산책자',
    );
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('save-profile-name')));
    await tester.pumpAndSettle();

    expect(find.text('도쿄 산책자'), findsNWidgets(2));
    expect(find.text('프로필 이름을 저장했어요.'), findsOneWidget);
    expect(find.text('변경사항 저장됨'), findsOneWidget);

    await tester.tap(find.byTooltip('마이페이지로 돌아가기'));
    await tester.pumpAndSettle();
    expect(find.text('도쿄 산책자'), findsOneWidget);
  });

  testWidgets('notification preferences can be changed from my page',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('알림 설정'), 300);
    await tester.drag(find.byType(ListView).first, const Offset(0, -120));
    await tester.pumpAndSettle();
    await tester.tap(find.text('알림 설정'));
    await tester.pumpAndSettle();

    expect(find.byType(SwitchListTile), findsNWidgets(2));
    expect(find.text('2개 앱 안내 사용 중'), findsOneWidget);
    await tester.tap(find.byType(SwitchListTile).first);
    await tester.pumpAndSettle();

    final switches = tester.widgetList<SwitchListTile>(
      find.byType(SwitchListTile),
    );
    expect(switches.first.value, isFalse);
    expect(find.text('1개 앱 안내 사용 중'), findsOneWidget);
  });

  testWidgets('mypage settings and help rows open dedicated pages',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    Future<void> openAndReturn(String menu, String expectedText) async {
      await tester.scrollUntilVisible(find.text(menu), 300);
      await tester.pumpAndSettle();
      await tester.tap(find.text(menu));
      await tester.pumpAndSettle();
      expect(find.text(expectedText), findsOneWidget);
      await tester.tap(find.byTooltip('마이페이지로 돌아가기'));
      await tester.pumpAndSettle();
    }

    await openAndReturn('언어 및 지역', '현재 지원 범위');
    await openAndReturn('앱 정보', '버전 정보');
    await openAndReturn('문의하기', 'support@chiwawa.app');
    await openAndReturn('이용 가이드', '내 여행 열기');
    await openAndReturn(
      '개인정보 및 위치 정보 안내',
      '공유 위치정보 기본값: 포함 안 함',
    );
  });

  testWidgets('mypage detail pages expose expanded context', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    Future<void> checkDetail(String menu, String detail) async {
      await tester.scrollUntilVisible(find.text(menu), 300);
      await tester.pumpAndSettle();
      await tester.tap(find.text(menu));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.text(detail),
        300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      expect(find.text(detail), findsOneWidget);
      await tester.tap(find.byTooltip('마이페이지로 돌아가기'));
      await tester.pumpAndSettle();
    }

    await checkDetail('언어 및 지역', '표기 예시');
    await checkDetail('앱 정보', 'chiwawa로 할 수 있는 일');
    await checkDetail('문의하기', '문의 전 확인');
    await checkDetail('이용 가이드', '도움이 더 필요할 때');
    await checkDetail('개인정보 및 위치 정보 안내', '내가 직접 관리할 수 있는 항목');
  });

  testWidgets('support page validates inquiry message', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('문의하기'), 300);
    await tester.pumpAndSettle();
    await tester.tap(find.text('문의하기'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('submit-support-inquiry')));
    await tester.pumpAndSettle();

    expect(find.text('문의 내용을 10자 이상 입력해 주세요.'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('support-diagnostics-switch')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('support-diagnostics-switch')),
        findsOneWidget);
    expect(find.textContaining('앱 버전: 1.0.0'), findsOneWidget);
    expect(find.textContaining('빌드 SHA: unknown'), findsOneWidget);
  });

  testWidgets('photo analysis candidates can be selected', (tester) async {
    useMobileTestSurface(tester);
    const candidates = [
      PhotoSearchResult(
        id: 'candidate-a',
        name: '첫 번째 장소',
        address: '도쿄',
        category: '명소',
        confidence: 0.91,
      ),
      PhotoSearchResult(
        id: 'candidate-b',
        name: '두 번째 장소',
        address: '도쿄',
        category: '공원',
        confidence: 0.71,
      ),
    ];
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreResultVisibleProvider.overrideWith((ref) => true),
          exploreCandidatesProvider.overrideWith((ref) => candidates),
          exploreSelectedResultProvider.overrideWith(
            (ref) => candidates.first,
          ),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('탐색'));
    await tester.pumpAndSettle();

    await tester.tap(
      find.byKey(const ValueKey('photo-candidate-candidate-b')),
    );
    await tester.pumpAndSettle();

    expect(find.text('사진 일치도 71%'), findsOneWidget);
    expect(find.text('두 번째 장소'), findsWidgets);
  });

  testWidgets('selected photo place can be corrected before saving',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreResultVisibleProvider.overrideWith((ref) => true),
          exploreSelectedResultProvider.overrideWith((ref) => _testPhotoResult),
          exploreCandidatesProvider.overrideWith((ref) => [_testPhotoResult]),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('탐색'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('장소 수정'));
    await tester.tap(find.text('장소 수정'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('place-correction-name')),
      '수정한 아사쿠사 장소',
    );
    await tester.tap(find.byKey(const ValueKey('save-place-correction')));
    await tester.pumpAndSettle();

    expect(find.text('수정한 아사쿠사 장소'), findsWidgets);
    expect(find.text('선택한 장소 정보를 수정했어요.'), findsOneWidget);
  });

  testWidgets('photo analysis failure offers inline recovery actions',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreImagePathProvider.overrideWith((ref) => 'failed-photo.jpg'),
          exploreAnalysisErrorProvider.overrideWith(
            (ref) => '사진 분석을 완료하지 못했어요.',
          ),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('탐색'));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('explore-analysis-failure')),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('retry-photo-analysis')), findsOneWidget);
    expect(find.byKey(const ValueKey('choose-another-photo')), findsOneWidget);
  });

  testWidgets('travel pace labels stay on one line at 320px', (tester) async {
    useNarrowTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.bySemanticsLabel('일정'));
    await tester.pumpAndSettle();

    await tester.dragUntilVisible(
      find.text('적당히'),
      find.byKey(const ValueKey('plan-scroll')),
      const Offset(0, -260),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(tester.getSize(find.text('적당히')).height, lessThan(24));
  });

  testWidgets('trip list switches the current trip and refreshes home',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.byTooltip('내 여행'));
    await tester.pumpAndSettle();

    expect(find.text('내 여행'), findsOneWidget);
    expect(find.text('도쿄 봄 여행'), findsOneWidget);
    expect(find.text('오사카 맛집 여행'), findsOneWidget);

    await tester.tap(find.text('오사카 맛집 여행'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('홈'));
    await tester.pumpAndSettle();

    expect(find.text('오사카 맛집 여행'), findsOneWidget);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('current_trip_id'), 'trip-osaka-food');
  });

  testWidgets('new trip is created and selected from the trip sheet',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.byTooltip('내 여행'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('open-trip-create')));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const ValueKey('trip-title-field')),
      '후쿠오카 주말 여행',
    );
    await tester.enterText(
      find.byKey(const ValueKey('trip-country-field')),
      '일본',
    );
    await tester.tap(find.byKey(const ValueKey('increase-travelers')));
    await tester.ensureVisible(
      find.byKey(const ValueKey('submit-trip-create')),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('submit-trip-create')));
    await tester.pumpAndSettle();

    expect(find.text('후쿠오카 주말 여행'), findsOneWidget);
    expect(find.text('일본 · 2명'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
  });

  testWidgets('chiwawa my page account row opens account screen',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('계정 연결'), 300);
    await tester.pumpAndSettle();
    await tester.tap(find.text('계정 연결'));
    await tester.pumpAndSettle();

    expect(find.text('게스트로 이용 중'), findsOneWidget);
    expect(find.text('계정 동기화 없이 현재 기기의 로컬 상태를 사용해요.'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('데이터 보관 방식'), 300);
    await tester.pumpAndSettle();
    expect(find.text('데이터 보관 방식'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('connect-google-account')));
    await tester.pumpAndSettle();

    expect(find.text('Google로 시작하기'), findsOneWidget);
    expect(find.text('로그인 없이 둘러보기'), findsOneWidget);
    expect(find.text('AI와 함께하는 자유여행 플래너'), findsOneWidget);
    expect(find.text('여행 일정'), findsNothing);
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

    expect(find.text('여행 일정'), findsOneWidget);

    await tester.tap(find.text('마이'));
    await tester.pumpAndSettle();

    expect(find.text('치와와 여행자'), findsOneWidget);

    await tester.scrollUntilVisible(find.text('계정 연결'), 300);
    await tester.pumpAndSettle();

    expect(find.text('traveler@chiwawa.app 연결됨'), findsOneWidget);
    await tester.tap(find.text('계정 연결'));
    await tester.pumpAndSettle();
    expect(find.text('Google 계정 연결됨'), findsOneWidget);
    expect(find.byKey(const ValueKey('account-logout')), findsOneWidget);
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

    await tester.scrollUntilVisible(find.text('계정 연결'), 300);
    await tester.pumpAndSettle();
    await tester.tap(find.text('계정 연결'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('account-logout')));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '로그아웃'));
    await tester.pumpAndSettle();

    expect(find.text('Google로 시작하기'), findsOneWidget);
    expect(find.text('오늘의 일정'), findsNothing);
  });

  testWidgets('Photo search result can be saved for plan building',
      (tester) async {
    useMobileTestSurface(tester);
    const analyzedResult = PhotoSearchResult(
      id: 'analyzed-place',
      name: '아사쿠사 센소지',
      address: '도쿄',
      category: '명소',
      confidence: 0.95,
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreResultVisibleProvider.overrideWith((ref) => true),
          exploreCandidatesProvider.overrideWith((ref) => [analyzedResult]),
          exploreSelectedResultProvider.overrideWith((ref) => analyzedResult),
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

    expect(find.text('아사쿠사 센소지 일정에 추가했어요.'), findsOneWidget);
    expect(find.text('일정 후보 저장됨'), findsOneWidget);

    await tester.ensureVisible(find.text('일정에 추가'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, '일정에 추가'));
    await tester.pump(const Duration(milliseconds: 250));

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(container.read(savedPhotoPlacesProvider), hasLength(1));
    expect(
      container.read(selectedPlacesProvider).map((place) => place.name),
      contains('아사쿠사 센소지'),
    );
  });

  testWidgets('Saved photo place appears on the plan screen', (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreResultVisibleProvider.overrideWith((ref) => true),
          exploreSelectedResultProvider.overrideWith((ref) => _testPhotoResult),
          exploreCandidatesProvider.overrideWith((ref) => [_testPhotoResult]),
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

    expect(
      find.text('사진으로 저장한 장소', skipOffstage: false),
      findsOneWidget,
    );
    expect(
      find.byKey(
        const ValueKey('select-saved-place-place-sensoji'),
        skipOffstage: false,
      ),
      findsOneWidget,
    );

    expect(
      find.widgetWithText(
        InputChip,
        '아사쿠사 센소지',
        skipOffstage: false,
      ),
      findsOneWidget,
    );
  });

  testWidgets('Saved photo place can be removed from plan saved section',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          exploreResultVisibleProvider.overrideWith((ref) => true),
          exploreSelectedResultProvider.overrideWith((ref) => _testPhotoResult),
          exploreCandidatesProvider.overrideWith((ref) => [_testPhotoResult]),
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
    final removeSavedPlaceButton = find
        .byKey(
          const ValueKey('remove-saved-place-place-sensoji'),
          skipOffstage: false,
        )
        .last;
    await tester.ensureVisible(removeSavedPlaceButton);
    await tester.pumpAndSettle();
    final removeButtonSize = tester.getSize(removeSavedPlaceButton);
    expect(removeButtonSize.width, greaterThanOrEqualTo(44));
    expect(removeButtonSize.height, greaterThanOrEqualTo(44));
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
    await selectPlanEndpoints(tester);

    await tester.ensureVisible(
      find.byKey(
        const ValueKey('plan-optimize-route'),
        skipOffstage: false,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(
      container.read(routeOptimizationProvider).status,
      AiJobStatus.done,
    );
    expect(find.text('최적 경로 결과'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('itinerary-summary-places')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('itinerary-summary-travel-time')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('itinerary-summary-cost')),
      findsOneWidget,
    );

    final optimizedNames = container
        .read(planItineraryProvider)
        .currentStops
        .map((stop) => stop.place.name)
        .toList(growable: false);
    await tester.ensureVisible(
      find.byKey(
        const ValueKey('confirm-route-button'),
        skipOffstage: false,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(
        const ValueKey('confirm-route-button'),
        skipOffstage: false,
      ),
    );
    await tester.pumpAndSettle();

    expect(container.read(routeOptimizationProvider).status, AiJobStatus.done);
    expect(
      container
          .read(planItineraryProvider)
          .currentStops
          .map((stop) => stop.place.name),
      optimizedNames,
    );
    expect(find.text('이 일정으로 확정했어요.'), findsOneWidget);
  });

  testWidgets('plan day constraints stay isolated and block invalid time',
      (tester) async {
    useNarrowTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.bySemanticsLabel('일정'));
    await tester.pumpAndSettle();

    expect(find.text('하루 시작과 마무리'), findsOneWidget);
    expect(find.text('09:00'), findsOneWidget);
    expect(find.text('20:00'), findsOneWidget);
    expect(
      find.text('검색 결과에서 출발지와 도착지를 선택해 주세요.'),
      findsOneWidget,
    );
    expect(find.text('최대 방문 장소'), findsNothing);

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    await tester.enterText(
      find.byKey(const ValueKey('plan-start-place-1')),
      '숙소',
    );
    await tester.pump(const Duration(milliseconds: 600));
    expect(
      container.read(planDayConstraintsProvider).forDay(1).startPlace,
      isNull,
    );
    await tester.tap(
      find.byKey(
        const ValueKey(
          'plan-start-place-result-1-mock-google-hotel-shinjuku',
        ),
      ),
    );
    await tester.pump();
    expect(
      container
          .read(planDayConstraintsProvider)
          .forDay(1)
          .startPlace
          ?.providerPlaceId,
      'mock-google-hotel-shinjuku',
    );

    await tester.enterText(
      find.byKey(const ValueKey('plan-end-place-1')),
      '하네다',
    );
    await tester.pump(const Duration(milliseconds: 600));
    final hanedaResult = find.byKey(
      const ValueKey(
        'plan-end-place-result-1-mock-google-haneda-airport',
      ),
    );
    await tester.ensureVisible(hanedaResult);
    await tester.pumpAndSettle();
    await tester.tap(hanedaResult);
    await tester.pumpAndSettle();

    container
        .read(planDayConstraintsProvider.notifier)
        .updateEndTime(1, '08:00');
    await tester.pumpAndSettle();

    expect(find.text('도착 시간은 출발 시간보다 늦어야 해요.'), findsOneWidget);
    final optimizeButton = tester.widget<ElevatedButton>(
      find.byKey(
        const ValueKey('plan-optimize-route'),
        skipOffstage: false,
      ),
    );
    expect(optimizeButton.onPressed, isNull);

    container
        .read(planDayConstraintsProvider.notifier)
        .updateEndTime(1, '20:00');
    await tester.pumpAndSettle();
    container.read(planItineraryProvider.notifier).selectDay(2);
    await tester.pumpAndSettle();

    expect(
      container.read(planDayConstraintsProvider).forDay(2).startPlace,
      isNull,
    );
    expect(
      container.read(planDayConstraintsProvider).forDay(1).startPlace?.name,
      '신주쿠 그랜드 호텔',
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('searching for a visit place preserves the selected endpoints',
      (tester) async {
    useNarrowTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.bySemanticsLabel('일정'));
    await tester.pumpAndSettle();
    await selectPlanEndpoints(tester);

    final visitSearch = find.byKey(
      const ValueKey('plan-visit-place-search'),
      skipOffstage: false,
    );
    await tester.ensureVisible(visitSearch);
    await tester.pumpAndSettle();
    await tester.enterText(visitSearch, '하네다');
    await tester.pump(const Duration(milliseconds: 600));

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    final constraint = container.read(planDayConstraintsProvider).forDay(1);
    expect(constraint.startPlace, _testStartPlace);
    expect(constraint.endPlace, _testEndPlace);
  });

  testWidgets('place candidates and time buttons fit at 390px', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('plan-start-place-1')),
      '도쿄역',
    );
    await tester.pump(const Duration(milliseconds: 600));

    expect(
      find.byKey(
        const ValueKey(
          'plan-start-place-result-1-mock-google-tokyo-station',
        ),
      ),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('plan-start-time-1')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey('plan-end-time-1')),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('mock optimization follows the configured start time',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();
    await selectPlanEndpoints(tester);

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    container
        .read(planDayConstraintsProvider.notifier)
        .updateStartTime(1, '10:30');
    await tester.pump();

    await tester.ensureVisible(
      find.byKey(
        const ValueKey('plan-optimize-route'),
        skipOffstage: false,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('plan-optimize-route')));
    await tester.pumpAndSettle();

    final itinerary = container.read(planItineraryProvider).currentStops;
    final routeResult = container.read(routeOptimizationProvider).result;
    expect(itinerary.length, greaterThan(4));
    expect(routeResult?.timeline?.plannedStartAt, contains('T10:30'));
    expect(itinerary.first.stopType, 'START');
    expect(itinerary[1].startTime, '10:42');
    expect(itinerary.last.stopType, 'END');
    expect(find.textContaining('대중교통 ·'), findsOneWidget);
  });

  testWidgets('transport selection changes mock route timeline and summary',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();
    await selectPlanEndpoints(tester);

    await tester.ensureVisible(
      find.byKey(
        const ValueKey('plan-optimize-route'),
        skipOffstage: false,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('plan-optimize-route')));
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(container.read(transportModeProvider), TransportMode.transit);
    expect(
      container.read(planItineraryProvider).currentStops[2].place.name,
      '하라주쿠 다케시타도리',
    );

    await tester.ensureVisible(
      find.byKey(const ValueKey('plan-transport-drive')),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('plan-transport-drive')));
    await tester.pumpAndSettle();

    expect(container.read(transportModeProvider), TransportMode.drive);
    expect(container.read(routeOptimizationProvider).status, AiJobStatus.done);

    expect(
      container.read(planItineraryProvider).currentStops[2].place.name,
      '시부야 스크램블',
    );
    expect(find.text('자동차 · 4곳'), findsOneWidget);
    expect(find.text('자동차 11분'), findsOneWidget);
    expect(find.text('약 27분'), findsOneWidget);
  });

  testWidgets('changing preferences ignores stale optimization result',
      (tester) async {
    useMobileTestSurface(tester);
    final repository = _ControlledPlanRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          planRepositoryProvider.overrideWithValue(repository),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();
    await selectPlanEndpoints(tester);

    await tester.ensureVisible(
      find.byKey(
        const ValueKey('plan-optimize-route'),
        skipOffstage: false,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('plan-optimize-route')));
    await tester.pump(const Duration(milliseconds: 250));
    await tester.dragUntilVisible(
      find.widgetWithText(FilterChip, '맛집'),
      find.byKey(const ValueKey('plan-scroll')),
      const Offset(0, -260),
    );
    await tester.pump();
    await tester.tap(find.widgetWithText(FilterChip, '맛집'));
    await tester.pump();

    repository.completer.complete(
      const RouteOptimizationResult.success(
        places: [
          RoutePlace(
            name: '이전 요청 결과',
            duration: '30분',
            transport: '도보',
            category: '명소',
          ),
        ],
      ),
    );
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(
      container.read(routeOptimizationProvider).status,
      AiJobStatus.idle,
    );
    expect(find.text('이전 요청 결과'), findsNothing);
  });

  testWidgets('Confirmed optimized route appears on memorial preview',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();
    await selectPlanEndpoints(tester);

    await tester.ensureVisible(
      find.byKey(
        const ValueKey('plan-optimize-route'),
        skipOffstage: false,
      ),
    );
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
    await selectPlanEndpoints(tester);

    await tester.ensureVisible(
      find.byKey(
        const ValueKey('plan-optimize-route'),
        skipOffstage: false,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ElevatedButton, 'AI 경로 최적화'));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.'), findsOneWidget);
    expect(find.text('다시 시도'), findsOneWidget);
  });

  testWidgets('Travel preference chips store enum state', (tester) async {
    useMobileTestSurface(tester);
    await pumpAppAsGuest(tester);

    await tester.tap(find.text('일정'));
    await tester.pumpAndSettle();

    await tester.dragUntilVisible(
      find.widgetWithText(FilterChip, '맛집'),
      find.byKey(const ValueKey('plan-scroll')),
      const Offset(0, -260),
    );
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

    final preferenceBottom = tester.getBottomRight(
      find.byType(AdaptiveSegmentedControl<TravelPace>),
    );
    final optimizeButtonTop = tester.getTopLeft(
      find.byKey(const ValueKey('plan-optimize-route')),
    );
    expect(
      optimizeButtonTop.dy,
      greaterThan(preferenceBottom.dy),
      reason: 'AI 경로 최적화 버튼은 추가 추천 조건 항목 아래에 있어야 한다.',
    );
  });
}
