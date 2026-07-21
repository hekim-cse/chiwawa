import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/api/api_trip_repository.dart';
import 'package:chiwawa/core/repositories/trip_repository.dart';
import 'package:chiwawa/core/services/trip_session_service.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  test('TripIdStore restores the selected trip', () async {
    final first = TripIdStore();
    await first.save('trip-selected');

    final restored = TripIdStore();
    await restored.restore();

    expect(restored.tripId, 'trip-selected');
  });

  test('ApiTripRepository follows trip list and CRUD paths', () async {
    final interceptor = _TripApiInterceptor();
    final dio = Dio(BaseOptions(baseUrl: 'https://example.test'))
      ..interceptors.add(interceptor);
    final store = TripIdStore();
    await store.save('trip-1');
    final repository = ApiTripRepository(dio: dio, tripIdStore: store);
    const draft = TripDraft(
      title: '오사카 여행',
      city: 'Osaka',
      startDate: '2026-08-01',
      endDate: '2026-08-04',
      travelers: 2,
      interests: ['food'],
      travelStyle: TravelPace.packed,
    );

    final trips = await repository.fetchTrips();
    final current = await repository.fetchCurrentTrip();
    final created = await repository.createTrip(draft);
    final updated = await repository.updateTrip('trip-created', draft);
    await repository.deleteTrip('trip-created');

    expect(trips.single.id, 'trip-1');
    expect(current.tripId, 'trip-1');
    expect(created.id, 'trip-created');
    expect(updated.travelStyle, TravelPace.packed);
    expect(
      interceptor.requests.map((request) => request.method),
      ['GET', 'GET', 'POST', 'PATCH', 'DELETE'],
    );
    expect(interceptor.requests[0].path, '/api/v1/trips');
    expect(interceptor.requests[1].path, '/api/v1/trips/trip-1');
    expect(
        interceptor.requests[2].data, containsPair('travel_style', 'packed'));
    expect(interceptor.requests[4].path, '/api/v1/trips/trip-created');
  });

  test('ApiTripRepository selects the first trip when no id is stored',
      () async {
    final interceptor = _TripApiInterceptor();
    final dio = Dio(BaseOptions(baseUrl: 'https://example.test'))
      ..interceptors.add(interceptor);
    final store = TripIdStore();
    final repository = ApiTripRepository(dio: dio, tripIdStore: store);

    final current = await repository.fetchCurrentTrip();

    expect(current.tripId, 'trip-1');
    expect(store.tripId, 'trip-1');
    expect(
      interceptor.requests.map((request) => request.path),
      ['/api/v1/trips', '/api/v1/trips/trip-1'],
    );
  });

  test('MockTripRepository stores its default trip on first load', () async {
    final store = TripIdStore();
    final repository = MockTripRepository(tripIdStore: store);

    final current = await repository.fetchCurrentTrip();

    expect(store.tripId, current.tripId);
  });
}

class _TripApiInterceptor extends Interceptor {
  final requests = <RequestOptions>[];

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    requests.add(options);

    if (options.method == 'DELETE') {
      handler.resolve(Response<void>(requestOptions: options, statusCode: 204));
      return;
    }

    final Object data;
    if (options.method == 'GET' && options.path == '/api/v1/trips') {
      data = const {
        'items': [_tripOne],
      };
    } else if (options.method == 'POST') {
      data = Map<String, Object?>.of(_tripOne)..['id'] = 'trip-created';
    } else if (options.method == 'PATCH') {
      data = Map<String, Object?>.of(_tripOne)
        ..['id'] = 'trip-created'
        ..['travel_style'] = 'packed';
    } else {
      data = _tripOne;
    }

    handler.resolve(
      Response<Object?>(
        requestOptions: options,
        statusCode: 200,
        data: data,
      ),
    );
  }
}

const _tripOne = <String, Object?>{
  'id': 'trip-1',
  'title': '도쿄 봄 여행',
  'city': 'Tokyo',
  'country': 'Japan',
  'start_date': '2026-04-01',
  'end_date': '2026-04-04',
  'travelers': 2,
  'interests': ['photo_spot'],
  'travel_style': 'balanced',
};
