import 'dart:convert';
import 'dart:typed_data';

import 'package:chiwawa/app/theme.dart';
import 'package:chiwawa/core/models/place_search_models.dart';
import 'package:chiwawa/core/models/route_planning_models.dart';
import 'package:chiwawa/core/models/transport_mode.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/plan_repository.dart';
import 'package:chiwawa/core/repositories/api/api_plan_repository.dart';
import 'package:chiwawa/core/saved_photo_places.dart';
import 'package:chiwawa/core/services/trip_session_service.dart';
import 'package:chiwawa/features/plan/models/plan_place_selection.dart';
import 'package:chiwawa/features/plan/plan_controller.dart';
import 'package:chiwawa/features/plan/plan_day_constraints_controller.dart';
import 'package:chiwawa/features/plan/widgets/plan_recommendations_section.dart';
import 'package:chiwawa/features/plan/widgets/route_optimization_section.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _recommendation = RouteRecommendation(
  candidate: RouteRecommendationCandidate(
    placeId: 'google-dessert-1',
    name: '핑크 디저트 라운지',
    formattedAddress: '도쿄 시부야구',
    latitude: 35.66,
    longitude: 139.7,
    rating: 4.7,
    userRatingCount: 321,
  ),
  insertionImpact: RouteInsertionImpact(
    previousPlaceId: 'wanted-seed:0',
    nextPlaceId: 'wanted-seed:1',
    additionalMinutes: 22,
    candidateArrivalAt: '2026-07-23T14:10',
    candidateDepartureAt: '2026-07-23T14:50',
    updatedNextArrivalAt: '2026-07-23T15:02',
    updatedTimelineEndAt: '2026-07-23T18:22',
  ),
);

const _recommendationGroup = RouteRecommendationGroup(
  category: 'DESSERT',
  displayName: '디저트',
  recommendations: [_recommendation],
);

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
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  test('editing endpoint times is not overwritten by confirmed route restore',
      () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final controller = container.read(routeOptimizationProvider.notifier);
    const result = RouteOptimizationResult.success(
      places: [],
      timeline: RouteTimeline(
        dayIndex: 1,
        travelMode: TransportMode.walk,
        plannedStartAt: '2026-08-01T09:00:00+02:00',
        plannedEndAt: '2026-08-01T20:00:00+02:00',
        actualEndAt: '2026-08-01T09:00:00+02:00',
        totalTravelMinutes: 0,
        totalStayMinutes: 0,
        timelineStops: [],
      ),
    );

    expect(controller.restoreConfirmed(1, result), isTrue);
    controller.reset();

    expect(controller.canRestoreConfirmed(1), isFalse);
    expect(controller.restoreConfirmed(1, result), isFalse);
  });

  test('timeline and recommendation contracts retain all UI fields', () {
    final timeline = RouteTimeline.fromJson(const {
      'day_index': 2,
      'travel_mode': 'TRANSIT',
      'planned_start_at': '2026-07-23T09:00',
      'planned_end_at': '2026-07-23T18:00',
      'actual_end_at': '2026-07-23T18:22',
      'total_travel_minutes': 71,
      'total_stay_minutes': 300,
      'exceeds_planned_end': true,
      'warnings': ['예정 종료를 22분 초과해요.'],
      'timeline_stops': [
        {
          'stop_type': 'POI',
          'place_id': 'wanted-1',
          'name': '첫 장소',
          'arrival_at': '2026-07-23T10:12',
          'departure_at': '2026-07-23T11:12',
          'stay_minutes': 60,
        },
      ],
    });
    final group = RouteRecommendationGroup.fromJson(const {
      'category': 'DESSERT',
      'display_name': '디저트',
      'recommendations': [
        {
          'candidate': {
            'place_id': 'google-dessert-1',
            'name': '핑크 디저트 라운지',
            'formatted_address': '도쿄 시부야구',
            'coordinate': {'latitude': 35.66, 'longitude': 139.7},
            'rating': 4.7,
            'user_rating_count': 321,
          },
          'insertion_impact': {
            'previous_place_id': 'wanted-1',
            'next_place_id': 'wanted-2',
            'additional_minutes': 22,
            'candidate_arrival_at': '2026-07-23T14:10',
            'candidate_departure_at': '2026-07-23T14:50',
            'updated_next_arrival_at': '2026-07-23T15:02',
            'updated_timeline_end_at': '2026-07-23T18:22',
          },
        },
      ],
    });

    expect(timeline.dayIndex, 2);
    expect(timeline.exceedsPlannedEnd, isTrue);
    expect(timeline.timelineStops.single.arrivalTime, '10:12');
    expect(timeline.timelineStops.single.departureTime, '11:12');
    expect(group.displayName, '디저트');
    expect(group.recommendations.single.insertionImpact.stayMinutes, 40);
    expect(
      group.recommendations.single.insertionImpact.updatedTimelineEndTime,
      '18:22',
    );
  });

  test('recommendation candidate rejects a response without coordinates', () {
    expect(
      () => RouteRecommendationCandidate.fromJson(const {
        'place_id': 'google-missing-coordinate',
        'name': '좌표 누락 장소',
      }),
      throwsA(isA<FormatException>()),
    );
  });

  test('route request excludes a selected place already used as an endpoint',
      () {
    const request = RouteOptimizationRequest(
      places: [
        PlanRoutePlaceInput(
          localId: 'endpoint-selection',
          serverPlaceId: 'wanted-start',
          providerPlaceId: 'google-start',
          name: '도쿄역',
        ),
        PlanRoutePlaceInput(
          localId: 'poi-selection',
          serverPlaceId: 'wanted-poi',
          providerPlaceId: 'google-poi',
          name: '도쿄 타워',
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
    );

    expect(request.wantedPlaceIds, ['wanted-poi']);
  });

  test('route optimization saves places first and forwards server ids',
      () async {
    final repository = _RecordingPlanRepository();
    final container = ProviderContainer(
      overrides: [
        planRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    _selectEndpoints(container);

    await container
        .read(routeOptimizationProvider.notifier)
        .optimize(TransportMode.transit);

    expect(repository.savedInputs.map((place) => place.name), ['첫 장소', '두 장소']);
    expect(
      repository.lastRequest?.wantedPlaceIds,
      ['wanted-seed:0', 'wanted-seed:1'],
    );
    expect(repository.lastRequest?.startPlace, _startPlace);
    expect(repository.lastRequest?.endPlace, _endPlace);
    expect(
      container
          .read(selectedPlacesProvider)
          .every((selection) => selection.isPersisted),
      isTrue,
    );
  });

  test('confirmed photo place is included in route optimization request',
      () async {
    final repository = _RecordingPlanRepository();
    final container = ProviderContainer(
      overrides: [
        planRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    _selectEndpoints(container);

    const photoPlace = PhotoSearchResult(
      id: 'photo-candidate-1',
      wantedPlaceId: 'wanted-photo-1',
      providerPlaceId: 'google-sacre-coeur',
      name: '사크레쾨르 대성당',
      address: '파리, 프랑스',
      category: '관광명소',
      latitude: 48.8867,
      longitude: 2.3431,
    );
    expect(
      container.read(planActionsProvider).addSavedPlace(photoPlace),
      isTrue,
    );

    await container
        .read(routeOptimizationProvider.notifier)
        .optimize(TransportMode.drive);

    expect(
      repository.lastRequest?.wantedPlaceIds,
      contains('wanted-photo-1'),
    );
    expect(
      repository.lastRequest?.places.map((place) => place.name),
      contains('사크레쾨르 대성당'),
    );
  });

  test('saved photo place is merged before route optimization', () async {
    final repository = _RecordingPlanRepository();
    final container = ProviderContainer(
      overrides: [
        planRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    _selectEndpoints(container);

    const photoPlace = PhotoSearchResult(
      id: 'photo-candidate-existing',
      wantedPlaceId: 'wanted-photo-existing',
      providerPlaceId: 'google-sacre-coeur',
      name: '사크레쾨르 대성당',
      address: '파리, 프랑스',
      category: '관광명소',
      latitude: 48.8867,
      longitude: 2.3431,
    );
    expect(
      container.read(savedPhotoPlacesProvider.notifier).addPlace(photoPlace),
      isTrue,
    );
    expect(
      container.read(selectedPlacesProvider).map((place) => place.name),
      isNot(contains('사크레쾨르 대성당')),
    );

    await container
        .read(routeOptimizationProvider.notifier)
        .optimize(TransportMode.drive);

    expect(
      repository.lastRequest?.wantedPlaceIds,
      contains('wanted-photo-existing'),
    );
    expect(
      container.read(selectedPlacesProvider).map((place) => place.name),
      contains('사크레쾨르 대성당'),
    );
  });

  test('a later save failure does not discard an earlier server id', () async {
    final repository = _RecordingPlanRepository(failOnSaveNumber: 2);
    final container = ProviderContainer(
      overrides: [
        planRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    _selectEndpoints(container);

    await container
        .read(routeOptimizationProvider.notifier)
        .optimize(TransportMode.transit);

    final selections = container.read(selectedPlacesProvider);
    expect(selections.first.serverPlaceId, 'wanted-seed:0');
    expect(selections.last.serverPlaceId, isNull);
    expect(
      container.read(routeOptimizationProvider).status,
      AiJobStatus.failed,
    );
  });

  test('API wanted-place response id is retained in the optimized stop',
      () async {
    final store = TripIdStore();
    await store.save('trip-route-contract');
    final dio = Dio();
    final adapter = _QueueHttpClientAdapter([
      {
        'id': 'wanted-server-1',
        'provider_place_id': 'google-tokyo-tower',
        'name': '도쿄 타워',
        'city': '도쿄',
        'country': '일본',
        'latitude': 35.6586,
        'longitude': 139.7454,
      },
      {
        'transport_mode': 'walk',
        'stops': [
          {
            'order': 1,
            'place_id': 'wanted-server-1',
            'name': '도쿄 타워',
            'estimated_travel_minutes': 9,
          },
        ],
        'timeline': {
          'day_index': 1,
          'travel_mode': 'WALK',
          'planned_start_at': '2026-08-01T09:00:00+09:00',
          'planned_end_at': '2026-08-01T18:00:00+09:00',
          'actual_end_at': '2026-08-01T10:09:00+09:00',
          'total_travel_minutes': 9,
          'total_stay_minutes': 60,
          'timeline_stops': [
            {
              'stop_type': 'POI',
              'place_id': 'wanted-server-1',
              'name': '도쿄 타워',
              'arrival_at': '2026-08-01T09:09:00+09:00',
              'departure_at': '2026-08-01T10:09:00+09:00',
              'stay_minutes': 60,
            },
          ],
          'warnings': <String>[],
        },
        'missing_segments': <String>[],
        'warnings': <String>[],
        'recommendation_groups': <Object?>[],
      },
      <String, Object?>{},
    ]);
    dio.httpClientAdapter = adapter;
    final repository = ApiPlanRepository(
      dio: dio,
      tripIdStore: store,
    );

    final saved = await repository.saveWantedPlace(
      const PlanRoutePlaceInput(
        localId: 'manual:1',
        providerPlaceId: 'google-tokyo-tower',
        name: '도쿄 타워',
        latitude: 35.6586,
        longitude: 139.7454,
      ),
    );
    final result = await repository.optimizeRoute(
      RouteOptimizationRequest(
        places: [
          PlanRoutePlaceInput(
            localId: 'manual:1',
            serverPlaceId: saved.id,
            providerPlaceId: saved.providerPlaceId,
            name: saved.name,
            latitude: saved.latitude,
            longitude: saved.longitude,
          ),
        ],
        preference: const TravelPreference(),
        transportMode: TransportMode.walk,
        dayIndex: 1,
        plannedStartTime: '09:00',
        plannedEndTime: '18:00',
        maxPlaceCount: 4,
        startPlace: _startPlace,
        endPlace: _endPlace,
      ),
    );
    await repository.confirmRoute(result);

    expect(saved.id, 'wanted-server-1');
    expect(adapter.requests.first.path, contains('/wanted-places'));
    expect(
      adapter.requests.last.path,
      contains('/route-optimizations/confirm'),
    );
    expect(adapter.requests[1].path, contains('/route-optimizations'));
    expect(
      adapter.requests[1].data,
      containsPair('transport_mode', 'walk'),
    );
    expect(
      adapter.requests.first.data,
      containsPair('provider_place_id', 'google-tokyo-tower'),
    );
    expect(result.places.single.placeId, 'wanted-server-1');
  });

  test('confirmed route API restores endpoints and the full timeline',
      () async {
    final store = TripIdStore();
    await store.save('trip-route-contract');
    final dio = Dio();
    final adapter = _QueueHttpClientAdapter([
      {
        'trip_id': 'trip-route-contract',
        'items': [
          {
            'day_index': 1,
            'start': {
              'place_id': 'google-hotel',
              'name': '파리 숙소',
              'lat': 48.8566,
              'lng': 2.3522,
            },
            'end': {
              'place_id': 'google-hotel',
              'name': '파리 숙소',
              'lat': 48.8566,
              'lng': 2.3522,
            },
            'route': {
              'transport_mode': 'walk',
              'stops': [
                {
                  'order': 1,
                  'place_id': 'wanted-louvre',
                  'name': '루브르 박물관',
                  'estimated_travel_minutes': 20,
                },
              ],
              'timeline': {
                'day_index': 1,
                'travel_mode': 'WALK',
                'planned_start_at': '2026-08-01T09:00:00+02:00',
                'planned_end_at': '2026-08-01T20:00:00+02:00',
                'actual_end_at': '2026-08-01T12:00:00+02:00',
                'total_travel_minutes': 60,
                'total_stay_minutes': 120,
                'timeline_stops': [
                  {
                    'stop_type': 'START',
                    'place_id': 'google-hotel',
                    'name': '파리 숙소',
                    'arrival_at': '2026-08-01T09:00:00+02:00',
                    'departure_at': '2026-08-01T09:00:00+02:00',
                    'stay_minutes': 0,
                  },
                  {
                    'stop_type': 'POI',
                    'place_id': 'wanted-louvre',
                    'name': '루브르 박물관',
                    'arrival_at': '2026-08-01T09:30:00+02:00',
                    'departure_at': '2026-08-01T11:30:00+02:00',
                    'stay_minutes': 120,
                  },
                  {
                    'stop_type': 'END',
                    'place_id': 'google-hotel',
                    'name': '파리 숙소',
                    'arrival_at': '2026-08-01T12:00:00+02:00',
                    'departure_at': '2026-08-01T12:00:00+02:00',
                    'stay_minutes': 0,
                  },
                ],
              },
              'missing_segments': <String>[],
              'warnings': <String>[],
              'recommendation_groups': <Object?>[],
            },
          },
        ],
      },
    ]);
    dio.httpClientAdapter = adapter;
    final repository = ApiPlanRepository(dio: dio, tripIdStore: store);

    final routes = await repository.fetchConfirmedRoutes();

    expect(adapter.requests.single.path,
        endsWith('/route-optimizations/confirmed'));
    expect(routes.single.startPlace.name, '파리 숙소');
    expect(routes.single.endPlace, routes.single.startPlace);
    expect(routes.single.result.timeline?.timelineStops, hasLength(3));
    expect(routes.single.result.places.single.name, '루브르 박물관');
  });

  test('adding a recommendation saves it and reoptimizes the route', () async {
    final repository = _RecordingPlanRepository();
    final container = ProviderContainer(
      overrides: [
        planRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    _selectEndpoints(container);

    await container
        .read(routeOptimizationProvider.notifier)
        .optimize(TransportMode.transit);
    final added = await container
        .read(planActionsProvider)
        .addRecommendation(_recommendation);

    final recommendationPlace = container
        .read(selectedPlacesProvider)
        .singleWhere((place) => place.source == PlanPlaceSource.freeTime);
    expect(added, isTrue);
    expect(recommendationPlace.serverPlaceId,
        'wanted-recommendation:google-dessert-1');
    expect(repository.optimizeCount, 2);
    expect(
      repository.lastRequest?.wantedPlaceIds,
      contains('wanted-recommendation:google-dessert-1'),
    );
    expect(
      container.read(routeOptimizationProvider).result?.recommendationGroups,
      isEmpty,
    );
  });

  test('saved recommendation is included when user optimizes later', () async {
    final repository = _RecordingPlanRepository();
    final container = ProviderContainer(
      overrides: [
        planRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);
    _selectEndpoints(container);

    final added = await container.read(planActionsProvider).addRecommendation(
          _recommendation,
          reoptimize: false,
        );

    expect(added, isTrue);
    expect(repository.optimizeCount, 0);

    await container
        .read(planActionsProvider)
        .optimizeRoute(TransportMode.transit);

    expect(repository.optimizeCount, 1);
    expect(
      repository.lastRequest?.wantedPlaceIds,
      contains('wanted-recommendation:google-dessert-1'),
    );
  });

  test('selected visit place preserves Google identity and coordinates',
      () async {
    final repository = _RecordingPlanRepository();
    final container = ProviderContainer(
      overrides: [
        planRepositoryProvider.overrideWithValue(repository),
      ],
    );
    addTearDown(container.dispose);

    final added = await container
        .read(planActionsProvider)
        .saveAndAddSearchedPlace(_startPlace);

    expect(added, isTrue);
    expect(repository.savedInputs.single.providerPlaceId,
        _startPlace.providerPlaceId);
    expect(repository.savedInputs.single.latitude, _startPlace.latitude);
    expect(
      container
          .read(selectedPlacesProvider)
          .singleWhere(
            (place) => place.providerPlaceId == _startPlace.providerPlaceId,
          )
          .providerPlaceId,
      _startPlace.providerPlaceId,
    );
  });

  testWidgets('unavailable route keeps the selected mode and shows reasons',
      (tester) async {
    await tester.pumpWidget(
      _testApp(
        RouteOptimizationSection(
          state: const RouteOptimizationState.done(
            RouteOptimizationResult.unavailable(
              warnings: ['대중교통 데이터가 충분하지 않아요.'],
              missingSegments: ['첫 장소 → 두 장소'],
            ),
          ),
          canOptimize: true,
          onOptimize: () {},
          onConfirm: () {},
          transportMode: TransportMode.transit,
        ),
      ),
    );

    expect(
        find.byKey(const ValueKey('route-option-unavailable')), findsOneWidget);
    expect(find.textContaining('자동으로 고르지 않았어요'), findsOneWidget);
    expect(find.textContaining('첫 장소 → 두 장소'), findsOneWidget);
    expect(find.byType(PlanRecommendationsSection), findsNothing);
  });

  testWidgets('server category drives recommendation preview and add action',
      (tester) async {
    var addCount = 0;
    await tester.pumpWidget(
      _testApp(
        SingleChildScrollView(
          child: PlanRecommendationsSection(
            groups: const [_recommendationGroup],
            onAdd: (_) async {
              addCount += 1;
              return true;
            },
          ),
        ),
      ),
    );

    expect(find.text('디저트'), findsOneWidget);
    expect(
      tester
          .getSemantics(
            find.byKey(
              const ValueKey('route-recommendation-google-dessert-1'),
            ),
          )
          .getSemanticsData()
          .hasAction(SemanticsAction.tap),
      isTrue,
    );
    await tester.tap(
      find.byKey(const ValueKey('route-recommendation-google-dessert-1')),
    );
    await tester.pump();
    expect(
      find.byKey(const ValueKey('route-recommendation-preview')),
      findsOneWidget,
    );
    expect(find.text('14:10~14:50'), findsOneWidget);
    expect(find.text('체류 40분'), findsOneWidget);
    expect(find.text('종료 18:22'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('add-route-recommendation')));
    await tester.pumpAndSettle();
    expect(addCount, 1);
  });
}

void _selectEndpoints(ProviderContainer container) {
  final controller = container.read(planDayConstraintsProvider.notifier);
  controller.selectStartPlace(1, _startPlace);
  controller.selectEndPlace(1, _endPlace);
}

Widget _testApp(Widget child) {
  return MaterialApp(
    theme: ChiwawaTheme.light(),
    home: Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: child,
        ),
      ),
    ),
  );
}

class _RecordingPlanRepository implements PlanRepository {
  _RecordingPlanRepository({this.failOnSaveNumber});

  final int? failOnSaveNumber;
  final List<PlanRoutePlaceInput> savedInputs = [];
  RouteOptimizationRequest? lastRequest;
  var optimizeCount = 0;

  @override
  List<String> get defaultSelectedPlaces => const ['첫 장소', '두 장소'];

  @override
  Future<void> confirmRoute(RouteOptimizationResult result) async {}

  @override
  Future<List<ConfirmedRoutePlan>> fetchConfirmedRoutes() async => const [];

  @override
  Future<WantedPlaceRecord> saveWantedPlace(
    PlanRoutePlaceInput place,
  ) async {
    savedInputs.add(place);
    if (savedInputs.length == failOnSaveNumber) {
      throw StateError('wanted-place save failed');
    }
    return WantedPlaceRecord(
      id: 'wanted-${place.localId}',
      name: place.name,
      address: place.address,
      latitude: place.latitude,
      longitude: place.longitude,
    );
  }

  @override
  Future<RouteOptimizationResult> optimizeRoute(
    RouteOptimizationRequest request,
  ) async {
    optimizeCount += 1;
    lastRequest = request;
    return RouteOptimizationResult.success(
      places: [
        for (final place in request.places)
          RoutePlace(
            placeId: place.serverPlaceId ?? '',
            name: place.name,
            duration: '60분',
            transport: '대중교통 12분',
            category: '명소',
          ),
      ],
      recommendationGroups: const [_recommendationGroup],
    );
  }
}

class _QueueHttpClientAdapter implements HttpClientAdapter {
  _QueueHttpClientAdapter(this.responses);

  final List<Map<String, Object?>> responses;
  final List<RequestOptions> requests = [];
  var _responseIndex = 0;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return ResponseBody.fromString(
      jsonEncode(responses[_responseIndex++]),
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
