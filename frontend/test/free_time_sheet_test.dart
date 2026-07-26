// 빈 시간 추천 바텀시트의 카테고리별 전체 후보 노출 테스트
import 'package:chiwawa/core/models/route_planning_models.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/providers/data_providers.dart';
import 'package:chiwawa/features/assist/widgets/free_time_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('선택한 카테고리의 Modal 추천만 렌더링한다', (tester) async {
    final recommendations = [
      _recommendation('1', '랜드마크·관광명소', '랜드마크 A'),
      _recommendation('2', '랜드마크·관광명소', '랜드마크 B'),
      _recommendation('3', '카페', '카페 A'),
      _recommendation('4', '카페', '카페 B'),
    ];

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          freeTimeRecommendsProvider.overrideWith(
            (ref) async => recommendations,
          ),
        ],
        child: const MaterialApp(
          home: Scaffold(body: FreeTimeRecommendSheet()),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('랜드마크·관광명소'), findsOneWidget);
    expect(find.text('카페'), findsOneWidget);
    expect(find.text('랜드마크 A'), findsOneWidget);
    expect(find.text('랜드마크 B'), findsOneWidget);
    expect(find.text('카페 A'), findsNothing);
    expect(find.text('카페 B'), findsNothing);

    await tester.tap(
      find.byKey(const ValueKey('free-time-category-카페')),
    );
    await tester.pumpAndSettle();

    expect(find.text('랜드마크 A'), findsNothing);
    expect(find.text('랜드마크 B'), findsNothing);
    expect(find.text('카페 A'), findsOneWidget);
    expect(find.text('카페 B'), findsOneWidget);
    expect(find.text('나중에'), findsNothing);
    expect(find.text('일정 후보에 추가'), findsNWidgets(2));
  });
}

FreeTimeRecommend _recommendation(
  String id,
  String category,
  String name,
) {
  return FreeTimeRecommend(
    id: id,
    dayIndex: 1,
    date: '2026-08-01',
    categoryLabel: category,
    name: name,
    walk: '10분',
    duration: '30분',
    recommendation: RouteRecommendation.fromJson({
      'candidate': {
        'place_id': 'google-$id',
        'name': name,
        'formatted_address': '주소 $id',
        'coordinate': {'latitude': 35.0, 'longitude': 135.0},
      },
    }),
  );
}
