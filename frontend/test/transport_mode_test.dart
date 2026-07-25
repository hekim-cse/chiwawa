import 'package:chiwawa/core/models/place_search_models.dart';
import 'package:chiwawa/core/models/route_planning_models.dart';
import 'package:chiwawa/core/models/transport_mode.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/plan_repository.dart';
import 'package:flutter_test/flutter_test.dart';

const _startPlace = PlaceSearchCandidate(
  providerPlaceId: 'google-start',
  name: '도쿄역',
  formattedAddress: '도쿄도 지요다구',
  latitude: 35.6812,
  longitude: 139.7671,
);

const _endPlace = PlaceSearchCandidate(
  providerPlaceId: 'google-end',
  name: '신주쿠 호텔',
  formattedAddress: '도쿄도 신주쿠구',
  latitude: 35.6896,
  longitude: 139.6917,
);

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
      PlanRoutePlaceInput(localId: 'a', name: '메이지 신궁'),
      PlanRoutePlaceInput(localId: 'b', name: '시부야 스크램블'),
    ];
    const preference = TravelPreference();

    final walk = await repository.optimizeRoute(
      const RouteOptimizationRequest(
        places: places,
        preference: preference,
        transportMode: TransportMode.walk,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '18:00',
        maxPlaceCount: 4,
        startPlace: _startPlace,
        endPlace: _endPlace,
      ),
    );
    final drive = await repository.optimizeRoute(
      const RouteOptimizationRequest(
        places: places,
        preference: preference,
        transportMode: TransportMode.drive,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '18:00',
        maxPlaceCount: 4,
        startPlace: _startPlace,
        endPlace: _endPlace,
      ),
    );
    final transit = await repository.optimizeRoute(
      const RouteOptimizationRequest(
        places: places,
        preference: preference,
        transportMode: TransportMode.transit,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '18:00',
        maxPlaceCount: 4,
        startPlace: _startPlace,
        endPlace: _endPlace,
      ),
    );

    expect(walk.places[1].transport, '도보 14분');
    expect(drive.places[1].name, '시부야 스크램블');
    expect(transit.places[1].name, '하라주쿠 다케시타도리');
    expect(
      {
        walk.places[1].transport,
        drive.places[1].transport,
        transit.places[1].transport,
      },
      hasLength(3),
    );
    expect(walk.timeline?.timelineStops.first.stopType, 'START');
    expect(walk.timeline?.timelineStops.first.placeId, 'google-start');
    expect(walk.timeline?.timelineStops.first.name, '도쿄역');
    expect(walk.timeline?.timelineStops.last.stopType, 'END');
    expect(walk.timeline?.timelineStops.last.placeId, 'google-end');
    expect(walk.timeline?.timelineStops.last.name, '신주쿠 호텔');
  });

  test('mock reoptimization keeps a newly added recommendation visible',
      () async {
    const repository = MockPlanRepository();
    final result = await repository.optimizeRoute(
      const RouteOptimizationRequest(
        places: [
          PlanRoutePlaceInput(localId: 'seed:0', name: '메이지 신궁'),
          PlanRoutePlaceInput(localId: 'seed:1', name: '하라주쿠'),
          PlanRoutePlaceInput(localId: 'seed:2', name: '오모테산도'),
          PlanRoutePlaceInput(localId: 'seed:3', name: '시부야'),
          PlanRoutePlaceInput(
            localId: 'recommendation:google-coffee',
            serverPlaceId: 'wanted-coffee',
            name: '오모테산도 로스터리',
          ),
        ],
        preference: TravelPreference(),
        transportMode: TransportMode.transit,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '20:00',
        maxPlaceCount: 4,
        startPlace: _startPlace,
        endPlace: _endPlace,
      ),
    );

    expect(result.places, hasLength(4));
    expect(
      result.places.any((place) => place.placeId == 'wanted-coffee'),
      isTrue,
    );
    expect(result.places.last.name, '오모테산도 로스터리');
  });

  test('transit route with an unsupported outskirts place is unavailable',
      () async {
    const repository = MockPlanRepository();
    final result = await repository.optimizeRoute(
      const RouteOptimizationRequest(
        places: [
          PlanRoutePlaceInput(localId: 'a', name: '메이지 신궁'),
          PlanRoutePlaceInput(localId: 'b', name: '오다이바 해변공원'),
        ],
        preference: TravelPreference(),
        transportMode: TransportMode.transit,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '20:00',
        maxPlaceCount: 4,
        startPlace: _startPlace,
        endPlace: _endPlace,
      ),
    );

    expect(result.isAvailable, isFalse);
    expect(result.missingSegments, contains('오다이바 해변공원'));
    expect(result.warnings, isNotEmpty);
    expect(result.timeline, isNull);
    expect(result.places, isEmpty);
  });

  test('walk and drive still succeed for the same outskirts place', () async {
    const repository = MockPlanRepository();
    const places = [
      PlanRoutePlaceInput(localId: 'a', name: '메이지 신궁'),
      PlanRoutePlaceInput(localId: 'b', name: '오다이바 해변공원'),
    ];

    for (final mode in [TransportMode.walk, TransportMode.drive]) {
      final result = await repository.optimizeRoute(
        RouteOptimizationRequest(
          places: places,
          preference: const TravelPreference(),
          transportMode: mode,
          dayIndex: 1,
          plannedStartTime: '09:00',
          plannedEndTime: '20:00',
          maxPlaceCount: 4,
          startPlace: _startPlace,
          endPlace: _endPlace,
        ),
      );
      expect(result.isAvailable, isTrue, reason: '${mode.label}은 정상이어야 한다');
      expect(result.timeline, isNotNull);
    }
  });
}
