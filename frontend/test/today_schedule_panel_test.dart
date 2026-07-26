// 홈 여행 일정이 확정 타임라인의 모든 장소를 노출하는지 검증하는 테스트
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/features/home/widgets/today_schedule_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('확정 일정이 6개를 넘어도 중간 장소를 생략하지 않는다', (tester) async {
    final schedules = [
      for (var index = 0; index < 8; index++)
        ScheduleItem(
          id: 'schedule-$index',
          tripId: 'trip-1',
          date: '2026-08-04',
          startTime: '${(9 + index).toString().padLeft(2, '0')}:00',
          name: index == 6 ? 'The Fire' : '장소 $index',
          placeId: 'place-$index',
          source: 'plan',
          stopType: index == 0
              ? 'START'
              : index == 7
                  ? 'END'
                  : 'POI',
        ),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: TodaySchedulePanel(
              tripInfo: const TripInfo(
                tripId: 'trip-1',
                tripName: '오사카 여행',
                city: '오사카',
                period: '2026.08.04',
                currentDay: '1일차',
                members: 1,
                weather: '',
              ),
              schedules: schedules,
              onFreeTap: () {},
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('The Fire'), findsOneWidget);
    expect(find.text('장소 5'), findsOneWidget);
    expect(find.text('도착 · 장소 7'), findsOneWidget);
  });
}
