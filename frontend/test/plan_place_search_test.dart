import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:chiwawa/core/models/place_search_models.dart';
import 'package:chiwawa/core/repositories/api/api_place_search_repository.dart';
import 'package:chiwawa/core/repositories/place_search_repository.dart';
import 'package:chiwawa/features/plan/plan_place_search_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

const _tokyoStation = PlaceSearchCandidate(
  providerPlaceId: 'google-tokyo-station',
  name: '도쿄역',
  formattedAddress: '도쿄도 지요다구 마루노우치 1-9-1',
  latitude: 35.6812,
  longitude: 139.7671,
);

const _hanedaAirport = PlaceSearchCandidate(
  providerPlaceId: 'google-haneda-airport',
  name: '하네다 공항',
  formattedAddress: '도쿄도 오타구 하네다쿠코',
  latitude: 35.5494,
  longitude: 139.7798,
);

void main() {
  test('a late response cannot overwrite the newest query results', () async {
    final repository = _ControlledPlaceSearchRepository();
    final controller = PlanPlaceSearchController(
      repository: repository,
      debounceDuration: Duration.zero,
    );
    addTearDown(controller.dispose);
    const key = PlanPlaceSearchKey(day: 1, role: PlanPlaceRole.start);

    controller.updateQuery(key, '도쿄');
    await Future<void>.delayed(Duration.zero);
    controller.updateQuery(key, '하네다');
    await Future<void>.delayed(Duration.zero);

    repository.complete('하네다', const [_hanedaAirport]);
    await Future<void>.delayed(Duration.zero);
    repository.complete('도쿄', const [_tokyoStation]);
    await Future<void>.delayed(Duration.zero);

    final state = controller.state.forKey(key);
    expect(state.query, '하네다');
    expect(state.status, PlanPlaceSearchStatus.success);
    expect(state.results, const [_hanedaAirport]);
  });

  test('empty, failure, and retry states remain explicit', () async {
    final repository = _QueuedPlaceSearchRepository([
      const <PlaceSearchCandidate>[],
      const PlaceSearchException('검색 서버에 연결하지 못했어요.'),
      const [_tokyoStation],
    ]);
    final controller = PlanPlaceSearchController(
      repository: repository,
      debounceDuration: const Duration(days: 1),
    );
    addTearDown(controller.dispose);
    const key = PlanPlaceSearchKey(day: 1, role: PlanPlaceRole.end);

    controller.updateQuery(key, '없는 장소');
    await controller.searchImmediately(key);
    expect(
      controller.state.forKey(key).status,
      PlanPlaceSearchStatus.empty,
    );

    controller.updateQuery(key, '도쿄역');
    await controller.searchImmediately(key);
    expect(
      controller.state.forKey(key).status,
      PlanPlaceSearchStatus.failure,
    );
    expect(
      controller.state.forKey(key).message,
      '검색 서버에 연결하지 못했어요.',
    );

    await controller.retry(key);
    expect(
      controller.state.forKey(key).status,
      PlanPlaceSearchStatus.success,
    );
    expect(controller.state.forKey(key).results, const [_tokyoStation]);
  });

  test('search state stays isolated by trip, day, and place role', () async {
    final store = PlanPlaceSearchStore();
    const repository = MockPlaceSearchRepository();
    final firstTrip = PlanPlaceSearchController(
      repository: repository,
      store: store,
      tripId: 'trip-a',
      debounceDuration: const Duration(days: 1),
    );
    final secondTrip = PlanPlaceSearchController(
      repository: repository,
      store: store,
      tripId: 'trip-b',
      debounceDuration: const Duration(days: 1),
    );
    addTearDown(firstTrip.dispose);
    addTearDown(secondTrip.dispose);
    const firstDayStart = PlanPlaceSearchKey(day: 1, role: PlanPlaceRole.start);
    const firstDayEnd = PlanPlaceSearchKey(day: 1, role: PlanPlaceRole.end);
    const secondDayStart =
        PlanPlaceSearchKey(day: 2, role: PlanPlaceRole.start);

    firstTrip.updateQuery(firstDayStart, '도쿄역');
    await firstTrip.searchImmediately(firstDayStart);
    firstTrip.updateQuery(firstDayEnd, '하네다');
    await firstTrip.searchImmediately(firstDayEnd);
    firstTrip.updateQuery(secondDayStart, '숙소');
    await firstTrip.searchImmediately(secondDayStart);
    secondTrip.updateQuery(firstDayStart, '나리타');
    await secondTrip.searchImmediately(firstDayStart);

    final restoredFirstTrip = PlanPlaceSearchController(
      repository: repository,
      store: store,
      tripId: 'trip-a',
    );
    addTearDown(restoredFirstTrip.dispose);

    expect(
      restoredFirstTrip.state.forKey(firstDayStart).results.single.name,
      '도쿄역',
    );
    expect(
      restoredFirstTrip.state.forKey(firstDayEnd).results.single.name,
      '하네다 공항',
    );
    expect(
      restoredFirstTrip.state.forKey(secondDayStart).results,
      hasLength(2),
    );
    expect(
      secondTrip.state.forKey(firstDayStart).results.single.name,
      '나리타 국제공항',
    );
  });

  test('selecting a result closes the candidate list with its exact name',
      () async {
    final controller = PlanPlaceSearchController(
      repository: const MockPlaceSearchRepository(),
    );
    addTearDown(controller.dispose);
    const key = PlanPlaceSearchKey(day: 3, role: PlanPlaceRole.start);

    controller.updateQuery(key, '도쿄');
    controller.selectPlace(key, _tokyoStation);

    final state = controller.state.forKey(key);
    expect(state.query, '도쿄역');
    expect(state.status, PlanPlaceSearchStatus.idle);
    expect(state.results, isEmpty);
  });

  test('API mode maps the backend place search contract', () async {
    final dio = Dio(BaseOptions(baseUrl: 'http://test'));
    final adapter = _PlaceSearchHttpAdapter();
    dio.httpClientAdapter = adapter;
    final repository = ApiPlaceSearchRepository(dio: dio);

    final result = await repository.searchPlaces('도쿄역', cityBias: 'Tokyo');

    expect(adapter.request?.path, '/api/v1/places/search');
    expect(adapter.request?.queryParameters, {
      'query': '도쿄역',
      'city_bias': 'Tokyo',
    });
    expect(result, const [_tokyoStation]);
  });
}

class _PlaceSearchHttpAdapter implements HttpClientAdapter {
  RequestOptions? request;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    request = options;
    return ResponseBody.fromString(
      jsonEncode({
        'items': [
          {
            'provider_place_id': 'google-tokyo-station',
            'name': '도쿄역',
            'formatted_address': '도쿄도 지요다구 마루노우치 1-9-1',
            'latitude': 35.6812,
            'longitude': 139.7671,
          },
        ],
      }),
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

class _ControlledPlaceSearchRepository implements PlaceSearchRepository {
  final Map<String, Completer<List<PlaceSearchCandidate>>> _requests = {};

  @override
  Future<List<PlaceSearchCandidate>> searchPlaces(
    String query, {
    String? cityBias,
  }) {
    final completer = Completer<List<PlaceSearchCandidate>>();
    _requests[query] = completer;
    return completer.future;
  }

  void complete(String query, List<PlaceSearchCandidate> results) {
    _requests[query]!.complete(results);
  }
}

class _QueuedPlaceSearchRepository implements PlaceSearchRepository {
  _QueuedPlaceSearchRepository(this._outcomes);

  final List<Object> _outcomes;
  var _nextOutcome = 0;

  @override
  Future<List<PlaceSearchCandidate>> searchPlaces(
    String query, {
    String? cityBias,
  }) async {
    final outcome = _outcomes[_nextOutcome++];
    if (outcome is PlaceSearchException) throw outcome;
    return outcome as List<PlaceSearchCandidate>;
  }
}
