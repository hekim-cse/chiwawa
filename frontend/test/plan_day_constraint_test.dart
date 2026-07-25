import 'package:chiwawa/core/models/place_search_models.dart';
import 'package:chiwawa/features/plan/models/plan_day_constraint.dart';
import 'package:chiwawa/features/plan/plan_day_constraints_controller.dart';
import 'package:flutter_test/flutter_test.dart';

const _hotel = PlaceSearchCandidate(
  providerPlaceId: 'google-hotel',
  name: '신주쿠 호텔',
  formattedAddress: '도쿄도 신주쿠구',
  latitude: 35.69,
  longitude: 139.69,
);

const _station = PlaceSearchCandidate(
  providerPlaceId: 'google-station',
  name: '도쿄역',
  formattedAddress: '도쿄도 지요다구',
  latitude: 35.68,
  longitude: 139.76,
);

const _airport = PlaceSearchCandidate(
  providerPlaceId: 'google-airport',
  name: '하네다 공항',
  formattedAddress: '도쿄도 오타구',
  latitude: 35.54,
  longitude: 139.77,
);

void main() {
  test('day constraint starts without an unverified place', () {
    const constraint = PlanDayConstraint();

    expect(constraint.startPlace, isNull);
    expect(constraint.startTime, '09:00');
    expect(constraint.endPlace, isNull);
    expect(constraint.endTime, '20:00');
    expect(constraint.maxPlaceCount, 4);
    expect(constraint.isValid, isFalse);
    expect(
      constraint.validationMessage,
      '검색 결과에서 출발지와 도착지를 선택해 주세요.',
    );
  });

  test('selected places retain provider id, address, and coordinates', () {
    final constraint = const PlanDayConstraint().copyWith(
      startPlace: _hotel,
      endPlace: _airport,
    );

    expect(constraint.startPlace?.providerPlaceId, 'google-hotel');
    expect(constraint.startPlace?.formattedAddress, '도쿄도 신주쿠구');
    expect(constraint.startPlace?.latitude, 35.69);
    expect(constraint.endPlace?.longitude, 139.77);
    expect(constraint.isValid, isTrue);
  });

  test('day constraint rejects an end time before the start time', () {
    final constraint = const PlanDayConstraint().copyWith(
      startPlace: _hotel,
      endPlace: _airport,
      startTime: '18:00',
      endTime: '17:30',
    );

    expect(constraint.isValid, isFalse);
    expect(constraint.validationMessage, '도착 시간은 출발 시간보다 늦어야 해요.');
  });

  test('day edits stay isolated and place count stays in range', () {
    final controller = PlanDayConstraintsController();
    addTearDown(controller.dispose);

    controller.selectStartPlace(1, _station);
    controller.updateStartTime(1, '10:30');
    controller.updateMaxPlaceCount(1, 99);
    controller.selectEndPlace(2, _airport);

    expect(controller.state.forDay(1).startPlace?.name, '도쿄역');
    expect(controller.state.forDay(1).startTime, '10:30');
    expect(
      controller.state.forDay(1).maxPlaceCount,
      PlanDayConstraint.maximumPlaceCount,
    );
    expect(controller.state.forDay(2).startPlace, isNull);
    expect(controller.state.forDay(2).endPlace?.name, '하네다 공항');
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

    firstTrip.selectStartPlace(1, _hotel);
    secondTrip.selectStartPlace(1, _station);

    final restoredFirstTrip = PlanDayConstraintsController(
      store: store,
      tripId: 'trip-a',
    );
    addTearDown(restoredFirstTrip.dispose);

    expect(restoredFirstTrip.state.forDay(1).startPlace, _hotel);
    expect(secondTrip.state.forDay(1).startPlace, _station);
  });
}
