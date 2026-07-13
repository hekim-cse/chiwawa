import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:chiwawa/app/theme.dart';
import 'package:chiwawa/core/models/memorial_map_models.dart';
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
