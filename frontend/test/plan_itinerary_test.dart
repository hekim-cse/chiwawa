import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/features/plan/plan_controller.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const places = [
    RoutePlace(
      name: '첫 장소',
      duration: '60분',
      transport: '도보 5분',
      category: '명소',
      travelCost: '무료',
    ),
    RoutePlace(
      name: '두 번째 장소',
      duration: '90분',
      transport: '지하철 12분',
      category: '전시',
      travelCost: '¥180',
    ),
  ];

  test('itinerary edits stay isolated by selected day', () {
    final controller = PlanItineraryController();
    addTearDown(controller.dispose);

    controller.replaceCurrentDay(places);
    final firstDayStopId = controller.state.currentStops.first.id;
    controller.updateTime(firstDayStopId, '10:30');
    controller.move(0, 1);

    expect(controller.state.currentStops.first.place.name, '두 번째 장소');
    expect(controller.state.currentStops.last.startTime, '10:30');

    controller.selectDay(2);
    expect(controller.state.currentStops, isEmpty);
    controller.replaceCurrentDay(places.reversed.toList());

    controller.selectDay(1);
    expect(controller.state.currentStops.first.place.name, '두 번째 장소');
    expect(controller.state.currentStops.last.startTime, '10:30');
  });

  test('itinerary delete removes only the selected stop', () {
    final controller = PlanItineraryController();
    addTearDown(controller.dispose);
    controller.replaceCurrentDay(places);

    controller.remove(controller.state.currentStops.first.id);

    expect(controller.state.currentStops, hasLength(1));
    expect(controller.state.currentStops.single.place.name, '두 번째 장소');
  });
}
