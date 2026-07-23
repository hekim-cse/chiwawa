import 'package:chiwawa/features/plan/models/plan_day_constraint.dart';
import 'package:chiwawa/features/plan/plan_day_constraints_controller.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('day constraint starts with demo-safe defaults', () {
    const constraint = PlanDayConstraint();

    expect(constraint.startPlace, '숙소');
    expect(constraint.startTime, '09:00');
    expect(constraint.endPlace, '숙소');
    expect(constraint.endTime, '20:00');
    expect(constraint.maxPlaceCount, 4);
    expect(constraint.isValid, isTrue);
  });

  test('day constraint rejects an end time before the start time', () {
    final constraint = const PlanDayConstraint().copyWith(
      startTime: '18:00',
      endTime: '17:30',
    );

    expect(constraint.isValid, isFalse);
    expect(constraint.validationMessage, '도착 시간은 출발 시간보다 늦어야 해요.');
  });

  test('day edits stay isolated and place count stays in range', () {
    final controller = PlanDayConstraintsController();
    addTearDown(controller.dispose);

    controller.updateStartPlace(1, '도쿄역');
    controller.updateStartTime(1, '10:30');
    controller.updateMaxPlaceCount(1, 99);
    controller.updateEndPlace(2, '하네다 공항');

    expect(controller.state.forDay(1).startPlace, '도쿄역');
    expect(controller.state.forDay(1).startTime, '10:30');
    expect(
      controller.state.forDay(1).maxPlaceCount,
      PlanDayConstraint.maximumPlaceCount,
    );
    expect(controller.state.forDay(2).startPlace, '숙소');
    expect(controller.state.forDay(2).endPlace, '하네다 공항');
  });

  test('stored constraints remain separate for each trip', () {
    final store = PlanDayConstraintStore();
    final firstTrip = PlanDayConstraintsController(
      store: store,
      tripId: 'trip-a',
    );
    final secondTrip = PlanDayConstraintsController(
      store: store,
      tripId: 'trip-b',
    );
    addTearDown(firstTrip.dispose);
    addTearDown(secondTrip.dispose);

    firstTrip.updateStartPlace(1, '첫 여행 숙소');
    secondTrip.updateStartPlace(1, '두 번째 여행 숙소');

    final restoredFirstTrip = PlanDayConstraintsController(
      store: store,
      tripId: 'trip-a',
    );
    addTearDown(restoredFirstTrip.dispose);

    expect(restoredFirstTrip.state.forDay(1).startPlace, '첫 여행 숙소');
    expect(secondTrip.state.forDay(1).startPlace, '두 번째 여행 숙소');
  });
}
