import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:chiwawa/app/theme.dart';
import 'package:chiwawa/core/models/memorial_map_models.dart';
import 'package:chiwawa/core/models/memorial_models.dart';
import 'package:chiwawa/core/repositories/memorial_repository.dart';
import 'package:chiwawa/features/memorial/memorial_photo_edits_controller.dart';
import 'package:chiwawa/features/memorial/widgets/paw_map_view.dart';
import 'package:chiwawa/main.dart';

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

  Future<void> openMemorial(WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: ChiwawaApp()));
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('기록'));
    await tester.pumpAndSettle();
  }

  PawCluster testCluster() {
    final photo = MemorialPhotoPoint(
      id: 'direct-photo',
      takenAt: DateTime(2025, 4, 1, 9),
      latitude: 35.7148,
      longitude: 139.7967,
      placeName: '초기 장소',
      assetPath: 'assets/images/mock/mock_memorial_01.png',
    );
    return PawCluster(
      id: 'direct-cluster',
      placeName: '초기 장소',
      latitude: photo.latitude,
      longitude: photo.longitude,
      arrivalTime: photo.takenAt,
      photos: [photo],
    );
  }

  Future<void> pumpDirectPawMap(
    WidgetTester tester, {
    bool disableAnimations = false,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ChiwawaTheme.light(),
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: disableAnimations),
          child: Scaffold(
            body: Padding(
              padding: const EdgeInsets.all(20),
              child: PawMapView(clusters: [testCluster()]),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets('Memorial paw map renders date strip and paw markers',
      (tester) async {
    useMobileTestSurface(tester);

    await openMemorial(tester);

    expect(find.text('발자국 지도'), findsOneWidget);
    expect(find.text('4월 1일 (화)'), findsOneWidget);

    await tester.pump(const Duration(seconds: 5));

    expect(
      find.byKey(const ValueKey('paw-marker-paw-photo-0401-asakusa-1')),
      findsOneWidget,
    );
    expect(find.byIcon(Icons.pets_rounded), findsAtLeastNWidgets(4));
    expect(find.text('다시 보기'), findsOneWidget);
  });

  testWidgets('Memorial paw marker opens photo sheet', (tester) async {
    useMobileTestSurface(tester);

    await openMemorial(tester);
    await tester.pump(const Duration(seconds: 5));

    await tester.tap(
      find.byKey(const ValueKey('paw-marker-paw-photo-0401-asakusa-1')),
    );
    await tester.pumpAndSettle();

    expect(find.text('아사쿠사 센소지'), findsOneWidget);
    expect(find.text('사진 2장'), findsOneWidget);
    expect(find.text('12:10 도착'), findsOneWidget);
  });

  testWidgets('Memorial photo location can be edited and photo can be excluded',
      (tester) async {
    useMobileTestSurface(tester);
    await openMemorial(tester);

    final menu = find.byKey(
      const ValueKey('memorial-photo-menu-photo-0401-narita-1'),
    );
    await tester.dragUntilVisible(
      menu,
      find.byKey(const ValueKey('memorial-scroll')),
      const Offset(0, -260),
    );
    await tester.pumpAndSettle();
    await tester.tap(menu);
    await tester.pumpAndSettle();
    await tester.tap(find.text('위치 수정'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('memorial-location-address')),
      '수정한 나리타 위치',
    );
    await tester.tap(find.byKey(const ValueKey('save-memorial-location')));
    await tester.pumpAndSettle();

    expect(find.text('사진 위치를 수정했어요.'), findsOneWidget);
    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChiwawaApp)),
    );
    expect(
      container
          .read(memorialPhotoEditsProvider)['photo-0401-narita-1']
          ?.address,
      '수정한 나리타 위치',
    );

    await tester.tap(menu);
    await tester.pumpAndSettle();
    await tester.tap(find.text('기록에서 제외'));
    await tester.pumpAndSettle();

    expect(
      container
          .read(memorialPhotoEditsProvider)['photo-0401-narita-1']
          ?.excluded,
      isTrue,
    );
    expect(menu, findsNothing);
  });

  testWidgets('Memorial date chip changes paw map data', (tester) async {
    useMobileTestSurface(tester);

    await openMemorial(tester);

    await tester.tap(find.text('4월 2일 (수)'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 5));

    expect(
      find.byKey(const ValueKey('paw-marker-paw-photo-0402-shibuya-1')),
      findsOneWidget,
    );
  });

  testWidgets('API memorial keeps unlocated photos in the photo list',
      (tester) async {
    useMobileTestSurface(tester);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memorialRepositoryProvider.overrideWithValue(
            const _ApiLikeMemorialRepository(),
          ),
        ],
        child: const ChiwawaApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('로그인 없이 둘러보기'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('기록'));
    await tester.pumpAndSettle();

    expect(find.text('2025년 4월'), findsOneWidget);
    expect(find.text('이날의 사진'), findsOneWidget);
    expect(find.text('위치 없는 사진 1장은 목록에만 보여요.'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('memorial-month-next')));
    await tester.pumpAndSettle();

    expect(find.text('2025년 5월'), findsOneWidget);
    expect(find.text('이 달에는 저장된 사진이 아직 없어요.'), findsOneWidget);
  });

  testWidgets('Memorial paw marker is tappable while route is playing',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpDirectPawMap(tester);

    await tester.tap(
      find.byKey(const ValueKey('paw-marker-direct-cluster')),
    );
    await tester.pumpAndSettle();

    expect(find.text('초기 장소'), findsOneWidget);
    expect(find.text('사진 1장'), findsOneWidget);
  });

  testWidgets('Memorial keeps selected paw context below the map',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpDirectPawMap(tester, disableAnimations: true);

    await tester.tap(
      find.byKey(const ValueKey('paw-marker-direct-cluster')),
    );
    await tester.pumpAndSettle();
    tester.state<NavigatorState>(find.byType(Navigator)).pop();
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('paw-map-selection-direct-cluster')),
      findsOneWidget,
    );
    expect(find.text('선택 위치 · 초기 장소'), findsOneWidget);
    expect(find.text('09:00 · 사진 1장'), findsOneWidget);
  });

  testWidgets('Memorial reduced motion renders without autoplay controls',
      (tester) async {
    useMobileTestSurface(tester);
    await pumpDirectPawMap(tester, disableAnimations: true);
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('paw-marker-direct-cluster')),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('paw-map-replay')), findsNothing);
  });

  testWidgets('Memorial replay resets and completes the paw map animation',
      (tester) async {
    useMobileTestSurface(tester);
    await openMemorial(tester);

    final replayButton = find.byKey(const ValueKey('paw-map-replay'));
    expect(replayButton, findsOneWidget);
    await tester.ensureVisible(replayButton);
    await tester.pumpAndSettle();
    await tester.tap(replayButton);
    await tester.pump();

    expect(
      find.byKey(const ValueKey('paw-map-replay-hidden')),
      findsOneWidget,
    );

    await tester.pump(const Duration(seconds: 4));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('paw-map-replay')), findsOneWidget);
  });
}

class _ApiLikeMemorialRepository implements MemorialRepository {
  const _ApiLikeMemorialRepository();

  @override
  Future<MemorialCalendar> fetchCalendar(MemorialMonth month) async {
    return MemorialCalendar(
      year: month.year,
      month: month.month,
      days: month == const MemorialMonth(2025, 4)
          ? [
              MemorialCalendarDay(
                day: DateTime(2025, 4, 7),
                photoCount: 2,
              ),
            ]
          : const [],
    );
  }

  @override
  Future<MemorialDayTimeline> fetchDay(DateTime day) async {
    if (day.year != 2025 || day.month != 4) {
      return MemorialDayTimeline(day: day, items: const []);
    }
    return MemorialDayTimeline(
      day: day,
      items: [
        MemorialTimelineEntry(
          seq: 0,
          photo: MemorialPhoto(
            id: 'api-located',
            fileName: 'located.jpg',
            contentType: 'image/jpeg',
            takenAt: DateTime(2025, 4, 7, 10),
            latitude: 35.7148,
            longitude: 139.7967,
            address: '아사쿠사',
            fileUrl: '/api/v1/memorial/photos/1/file',
          ),
        ),
        MemorialTimelineEntry(
          seq: 1,
          photo: MemorialPhoto(
            id: 'api-unlocated',
            fileName: 'unlocated.jpg',
            contentType: 'image/jpeg',
            takenAt: DateTime(2025, 4, 7, 11),
            fileUrl: '/api/v1/memorial/photos/2/file',
          ),
        ),
      ],
    );
  }

  @override
  Future<MemorialOverview?> fetchOverview() async => null;

  @override
  Future<Uint8List> fetchPhotoBytes(String fileUrl) async => Uint8List(0);
}
