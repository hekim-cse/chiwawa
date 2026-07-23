import 'package:chiwawa/core/models/route_planning_models.dart';
import 'package:chiwawa/core/models/transport_mode.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/plan_repository.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('transport mode exposes Korean, backend, and AI values', () {
    expect(TransportMode.walk.label, '도보');
    expect(TransportMode.drive.backendCode, 'drive');
    expect(TransportMode.transit.aiCode, 'TRANSIT');
  });

  test('transport mode decodes backend and AI codes in both cases', () {
    expect(
      TransportModeMapping.fromBackendCode('walk'),
      TransportMode.walk,
    );
    expect(
      TransportModeMapping.fromAiCode('DRIVE'),
      TransportMode.drive,
    );
    expect(
      TransportModeMapping.fromBackendCode('unknown'),
      TransportMode.transit,
    );
  });

  test('mock repository returns different route details by transport',
      () async {
    const repository = MockPlanRepository();
    const places = [
      PlanRoutePlaceInput(localId: 'place-1', name: '메이지 신궁'),
      PlanRoutePlaceInput(localId: 'place-2', name: '시부야 스크램블'),
    ];
    const preference = TravelPreference();

    final walk = await repository.optimizeRoute(
      const RouteOptimizationRequest(
        places: places,
        preference: preference,
        transportMode: TransportMode.walk,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '20:00',
        maxPlaceCount: 4,
      ),
    );
    final drive = await repository.optimizeRoute(
      const RouteOptimizationRequest(
        places: places,
        preference: preference,
        transportMode: TransportMode.drive,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '20:00',
        maxPlaceCount: 4,
      ),
    );
    final transit = await repository.optimizeRoute(
      const RouteOptimizationRequest(
        places: places,
        preference: preference,
        transportMode: TransportMode.transit,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '20:00',
        maxPlaceCount: 4,
      ),
    );

    expect(walk[1].transport, '도보 14분');
    expect(drive[1].name, '시부야 스크램블');
    expect(transit[1].name, '하라주쿠 다케시타도리');
    expect({walk[1].transport, drive[1].transport, transit[1].transport},
        hasLength(3));
  });
}
