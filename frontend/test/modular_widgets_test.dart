import 'package:chiwawa/app/theme.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/saved_photo_places.dart';
import 'package:chiwawa/features/explore/widgets/candidate_selector.dart';
import 'package:chiwawa/features/home/widgets/home_quick_actions.dart';
import 'package:chiwawa/features/plan/widgets/route_optimization_section.dart';
import 'package:chiwawa/features/plan/models/plan_itinerary.dart';
import 'package:chiwawa/features/plan/widgets/plan_day_selector.dart';
import 'package:chiwawa/features/plan/widgets/plan_itinerary_workspace.dart';
import 'package:chiwawa/features/trips/widgets/trip_list_item.dart';
import 'package:chiwawa/features/mypage/widgets/my_page_detail_scaffold.dart';
import 'package:chiwawa/shared/widgets/adaptive_segmented_control.dart';
import 'package:chiwawa/shared/widgets/app_list_group.dart';
import 'package:chiwawa/shared/widgets/app_status_view.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Widget app(Widget child) {
    return MaterialApp(
      theme: ChiwawaTheme.light(),
      home: Scaffold(body: SafeArea(child: child)),
    );
  }

  test('primary copy uses the shared deep rose text color', () {
    final theme = ChiwawaTheme.light();

    expect(ChiwawaColors.textPrimary, const Color(0xFF5A2F3B));
    expect(theme.colorScheme.onSurface, ChiwawaColors.textPrimary);
    expect(theme.textTheme.bodyMedium?.color, ChiwawaColors.textPrimary);
  });

  test('interaction foundation keeps pink states and neutral borders', () {
    final theme = ChiwawaTheme.light();

    expect(
      theme.navigationBarTheme.height,
      ChiwawaControlSizes.navigationBar,
    );
    expect(
      theme.switchTheme.trackColor?.resolve({WidgetState.selected}),
      ChiwawaColors.primary,
    );
    expect(
      theme.switchTheme.trackColor?.resolve(<WidgetState>{}),
      ChiwawaColors.border,
    );
    expect(
      theme.outlinedButtonTheme.style?.side?.resolve(<WidgetState>{})?.color,
      ChiwawaColors.border,
    );
  });

  testWidgets('shared selectors use the 48px interaction height',
      (tester) async {
    var selected = 1;
    await tester.pumpWidget(
      app(
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AdaptiveSegmentedControl<int>(
              segments: const [
                AdaptiveSegment(value: 1, label: '첫 번째'),
                AdaptiveSegment(value: 2, label: '두 번째'),
              ],
              selected: selected,
              onSelected: (value) => selected = value,
            ),
            PlanDaySelector(
              selectedDay: 1,
              dayCount: 2,
              onSelected: (value) => selected = value,
            ),
          ],
        ),
      ),
    );

    expect(
      tester.getSize(find.byType(AdaptiveSegmentedControl<int>)).height,
      ChiwawaControlSizes.minimumInteractive,
    );
    expect(
      tester.getSize(find.byType(PlanDaySelector)).height,
      ChiwawaControlSizes.minimumInteractive,
    );
    await tester.tap(find.text('두 번째'));
    expect(selected, 2);
  });

  testWidgets('quick actions grow to another row and keep callbacks isolated',
      (tester) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final tapped = <String>[];
    await tester.pumpWidget(
      app(
        Padding(
          padding: const EdgeInsets.all(16),
          child: Align(
            alignment: Alignment.topCenter,
            child: HomeQuickActions(
              actions: [
                HomeQuickActionData(
                  id: 'first',
                  icon: Icons.looks_one_rounded,
                  label: '첫 번째',
                  onTap: () => tapped.add('first'),
                ),
                HomeQuickActionData(
                  id: 'second',
                  icon: Icons.looks_two_rounded,
                  label: '두 번째',
                  onTap: () => tapped.add('second'),
                ),
                HomeQuickActionData(
                  id: 'third',
                  icon: Icons.looks_3_rounded,
                  label: '세 번째',
                  onTap: () => tapped.add('third'),
                ),
                HomeQuickActionData(
                  id: 'fourth',
                  icon: Icons.looks_4_rounded,
                  label: '네 번째',
                  onTap: () => tapped.add('fourth'),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    expect(
        find.byKey(const ValueKey('home-quick-action-fourth')), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('네 번째'));
    expect(tapped, ['fourth']);
  });

  testWidgets('shared list row keeps long text and trailing value readable',
      (tester) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    var tapped = false;
    await tester.pumpWidget(
      app(
        Padding(
          padding: const EdgeInsets.all(16),
          child: AppListGroup(
            children: [
              AppListRow(
                title: '아주 긴 한국어 장소 이름도 두 줄 안에서 안정적으로 보여요',
                subtitle: '선택한 여행에 연결된 상세 정보',
                leading: const AppLeadingIcon(icon: Icons.place_rounded),
                trailing: const Text('현재 여행'),
                showDivider: false,
                onTap: () => tapped = true,
              ),
            ],
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.text('현재 여행'), findsOneWidget);
    await tester.tap(find.textContaining('아주 긴 한국어'));
    expect(tapped, isTrue);
  });

  testWidgets('shared status view exposes one recovery action', (tester) async {
    var retried = false;
    await tester.pumpWidget(
      app(
        AppStatusView(
          kind: AppStatusKind.error,
          title: '내용을 불러오지 못했어요',
          message: '연결을 확인해 주세요.',
          actionLabel: '다시 시도',
          onAction: () => retried = true,
        ),
      ),
    );

    await tester.tap(find.text('다시 시도'));
    expect(retried, isTrue);
  });

  testWidgets('my page info row stacks long values on narrow screens',
      (tester) async {
    tester.view.physicalSize = const Size(320, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      app(
        const Padding(
          padding: EdgeInsets.all(16),
          child: MyPageSection(
            child: MyPageInfoRow(
              label: '아주 긴 설정 이름',
              value: '줄바꿈이 필요한 아주 긴 현재 선택 값',
              showDivider: false,
            ),
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    final labelTop = tester.getTopLeft(find.text('아주 긴 설정 이름')).dy;
    final valueTop = tester.getTopLeft(find.text('줄바꿈이 필요한 아주 긴 현재 선택 값')).dy;
    expect(valueTop, greaterThan(labelTop));
  });

  testWidgets('trips with the same title select by trip id', (tester) async {
    String? selectedId;
    Trip trip(String id, String city) => Trip(
          id: id,
          title: '같은 이름 여행',
          city: city,
          country: 'Japan',
          startDate: '2026-08-01',
          endDate: '2026-08-03',
          travelers: 2,
          interests: const [],
          travelStyle: TravelPace.balanced,
        );

    await tester.pumpWidget(
      app(
        ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TripListItem(
              trip: trip('trip-a', '도쿄'),
              isCurrent: false,
              onTap: () => selectedId = 'trip-a',
            ),
            const SizedBox(height: 10),
            TripListItem(
              trip: trip('trip-b', '오사카'),
              isCurrent: false,
              onTap: () => selectedId = 'trip-b',
            ),
          ],
        ),
      ),
    );

    expect(find.text('같은 이름 여행'), findsNWidgets(2));
    await tester.tap(find.byKey(const ValueKey('trip-card-trip-b')));
    expect(selectedId, 'trip-b');
  });

  testWidgets('same-name candidates invoke the selected id callback',
      (tester) async {
    const candidates = [
      PhotoSearchResult(
        id: 'candidate-a',
        name: '같은 장소',
        address: '도쿄 1',
        category: '명소',
        confidence: 0.8,
      ),
      PhotoSearchResult(
        id: 'candidate-b',
        name: '같은 장소',
        address: '도쿄 2',
        category: '공원',
        confidence: 0.7,
      ),
    ];
    String? selectedId;

    await tester.pumpWidget(
      app(
        Padding(
          padding: const EdgeInsets.all(16),
          child: CandidateSelector(
            candidates: candidates,
            selected: candidates.first,
            onSelected: (candidate) => selectedId = candidate.id,
          ),
        ),
      ),
    );

    await tester.tap(
      find.byKey(const ValueKey('photo-candidate-candidate-b')),
    );
    expect(selectedId, 'candidate-b');
  });

  testWidgets('duplicate route rows render independently', (tester) async {
    const repeatedPlace = RoutePlace(
      name: '반복 장소',
      duration: '45분',
      transport: '도보 5분',
      category: '명소',
    );

    await tester.pumpWidget(
      app(
        const SingleChildScrollView(
          padding: EdgeInsets.all(16),
          child: RouteOptimizationSection(
            state: RouteOptimizationState.done([
              repeatedPlace,
              repeatedPlace,
            ]),
            canOptimize: true,
            onOptimize: _noop,
            onConfirm: _noop,
          ),
        ),
      ),
    );

    expect(find.text('반복 장소'), findsNWidgets(2));
    expect(tester.takeException(), isNull);
  });

  testWidgets('itinerary workspace keeps time cost and edit callbacks aligned',
      (tester) async {
    const first = PlanItineraryStop(
      id: 'first-stop',
      startTime: '09:00',
      place: RoutePlace(
        name: '첫 장소',
        duration: '60분',
        transport: '도보 5분',
        category: '명소',
      ),
    );
    const second = PlanItineraryStop(
      id: 'second-stop',
      startTime: '11:00',
      place: RoutePlace(
        name: '두 번째 장소',
        duration: '90분',
        transport: '지하철 12분',
        category: '전시',
        travelCost: '¥180',
      ),
    );
    String? editedId;

    await tester.pumpWidget(
      app(
        SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: PlanItineraryWorkspace(
            stops: const [first, second],
            onEditTime: (stop) => editedId = stop.id,
            onConfirm: _noop,
          ),
        ),
      ),
    );

    expect(find.text('지하철 12분'), findsOneWidget);
    expect(find.text('¥180'), findsNWidgets(2));
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('itinerary-summary-cost')),
        matching: find.text('¥180'),
      ),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const ValueKey('itinerary-time-second-stop')));
    expect(editedId, 'second-stop');
    expect(tester.takeException(), isNull);
  });

  test('saved places with the same label remain isolated by id', () {
    final notifier = SavedPhotoPlacesNotifier();
    addTearDown(notifier.dispose);
    const first = PhotoSearchResult(
      id: 'place-a',
      name: '같은 장소',
      address: '같은 주소',
      category: '명소',
    );
    const second = PhotoSearchResult(
      id: 'place-b',
      name: '같은 장소',
      address: '같은 주소',
      category: '명소',
    );

    expect(notifier.addPlace(first), isTrue);
    expect(notifier.addPlace(second), isTrue);
    notifier.removePlace(second);

    expect(notifier.state, [first]);
  });
}

void _noop() {}
