import 'dart:convert';
import 'dart:typed_data';

import 'package:chiwawa/core/models/route_planning_models.dart';
import 'package:chiwawa/core/models/transport_mode.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/api/api_plan_repository.dart';
import 'package:chiwawa/core/repositories/plan_repository.dart';
import 'package:chiwawa/core/services/trip_session_service.dart';
import 'package:chiwawa/features/plan/plan_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
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

    await container
        .read(routeOptimizationProvider.notifier)
        .optimize(TransportMode.transit);

    expect(repository.savedInputs.map((place) => place.name), ['첫 장소', '두 장소']);
    expect(
      repository.lastRequest?.wantedPlaceIds,
      ['wanted-seed:0', 'wanted-seed:1'],
    );
    expect(
      container
          .read(selectedPlacesProvider)
          .every((selection) => selection.isPersisted),
      isTrue,
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

  test('API wanted-place response id is retained in optimized stop', () async {
    final store = TripIdStore();
    await store.save('trip-route-contract');
    final dio = Dio();
    final adapter = _QueueHttpClientAdapter([
      {
        'id': 'wanted-server-1',
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
      },
    ]);
    dio.httpClientAdapter = adapter;
    final repository = ApiPlanRepository(dio: dio, tripIdStore: store);

    final saved = await repository.saveWantedPlace(
      const PlanRoutePlaceInput(
        localId: 'manual:1',
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
      ),
    );

    expect(saved.id, 'wanted-server-1');
    expect(adapter.requests.first.path, contains('/wanted-places'));
    expect(adapter.requests.last.path, contains('/route-optimizations'));
    expect(adapter.requests.last.data, containsPair('transport_mode', 'walk'));
    expect(result.single.placeId, 'wanted-server-1');
  });
}

class _RecordingPlanRepository implements PlanRepository {
  _RecordingPlanRepository({this.failOnSaveNumber});

  final int? failOnSaveNumber;
  final List<PlanRoutePlaceInput> savedInputs = [];
  RouteOptimizationRequest? lastRequest;

  @override
  List<String> get defaultSelectedPlaces => const ['첫 장소', '두 장소'];

  @override
  Future<WantedPlaceRecord> saveWantedPlace(
    PlanRoutePlaceInput place,
  ) async {
    savedInputs.add(place);
    if (savedInputs.length == failOnSaveNumber) {
      throw StateError('save failed');
    }
    return WantedPlaceRecord(
      id: 'wanted-${place.localId}',
      name: place.name,
    );
  }

  @override
  Future<List<RoutePlace>> optimizeRoute(
    RouteOptimizationRequest request,
  ) async {
    lastRequest = request;
    return [
      for (final place in request.places)
        RoutePlace(
          placeId: place.serverPlaceId ?? '',
          name: place.name,
          duration: '60분',
          transport: request.transportMode.label,
          category: '',
        ),
    ];
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
    final response = responses[_responseIndex++];
    return ResponseBody.fromString(
      jsonEncode(response),
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
