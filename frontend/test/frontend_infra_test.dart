import 'dart:typed_data';

import 'package:chiwawa/core/api/api_exception.dart';
import 'package:chiwawa/core/api/dio_client.dart';
import 'package:chiwawa/core/auth/auth_controller.dart';
import 'package:chiwawa/core/auth/deep_link_service.dart';
import 'package:chiwawa/core/confirmed_route.dart';
import 'package:chiwawa/core/repositories/api/api_plan_repository.dart';
import 'package:chiwawa/core/models/transport_mode.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/saved_photo_places.dart';
import 'package:chiwawa/core/services/trip_session_service.dart';
import 'package:chiwawa/core/utils/time_formatters.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  test('formatTime strips backend seconds from time strings', () {
    expect(formatTime('08:45:00'), '08:45');
    expect(formatTime('08:45'), '08:45');
    expect(formatTime('8:5:00'), '08:05');
    expect(formatTime(''), '');
  });

  test('ScheduleItem exposes UI time without seconds', () {
    final schedule = ScheduleItem.fromJson(const {
      'id': 'schedule-1',
      'trip_id': 'trip-1',
      'name': '아사쿠사 센소지',
      'date': '2025-04-03',
      'start_time': '09:00:00',
      'source': 'manual',
    });

    expect(schedule.startTime, '09:00:00');
    expect(schedule.time, '09:00');
  });

  test('ApiException extracts FastAPI detail responses', () {
    final requestOptions = RequestOptions(path: '/trips/stale');
    final error = DioException(
      requestOptions: requestOptions,
      response: Response<Object?>(
        requestOptions: requestOptions,
        statusCode: 404,
        data: const {'detail': 'Trip not found'},
      ),
      type: DioExceptionType.badResponse,
    );

    final apiError = ApiException.fromDioException(error);

    expect(apiError.message, 'Trip not found');
    expect(apiError.isNotFound, isTrue);
    expect(mapApiErrorToMessage(error), 'Trip not found');
  });

  test('ApiException falls back for network errors without detail', () {
    final error = DioException(
      requestOptions: RequestOptions(path: '/health'),
      type: DioExceptionType.connectionError,
      error: const SocketExceptionStub(),
    );

    expect(
      ApiException.fromDioException(error).message,
      '서버에 연결하지 못했어요. 네트워크 상태를 확인해 주세요.',
    );
  });

  test('TripSessionService recreates trip and retries after 404', () async {
    final store = TripIdStore();
    await store.save('stale-trip');
    final service = TripSessionService(store);
    final requestedTripIds = <String>[];
    var createCount = 0;

    final result = await service.loadWithRecovery<String>(
      loadTrip: (tripId) async {
        requestedTripIds.add(tripId);
        if (tripId == 'stale-trip') {
          throw const ApiException('Trip not found', statusCode: 404);
        }
        return 'loaded-$tripId';
      },
      createTrip: () async {
        createCount += 1;
        return 'fresh-trip';
      },
    );

    expect(result, 'loaded-fresh-trip');
    expect(store.tripId, 'fresh-trip');
    expect(requestedTripIds, ['stale-trip', 'fresh-trip']);
    expect(createCount, 1);
  });

  test('DeepLinkService exchanges OAuth code and stores auth session',
      () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final handled = await container
        .read(deepLinkServiceProvider)
        .handleAuthRedirect(Uri.parse('chiwawa://auth?code=google-code'));

    final auth = container.read(authControllerProvider);
    expect(handled, isTrue);
    expect(auth.isSignedIn, isTrue);
    expect(auth.token, 'mock-jwt-token');
    expect(container.read(authTokenProvider), 'mock-jwt-token');
    expect(auth.user?.email, 'traveler@chiwawa.app');
  });

  test('DeepLinkService ignores auth redirects without OAuth code', () async {
    // 계약 기준: code만 처리한다. token 직접 전달은 계약에 없어 무시한다.
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final handled = await container
        .read(deepLinkServiceProvider)
        .handleAuthRedirect(Uri.parse('chiwawa://auth?token=legacy-token'));

    expect(handled, isFalse);
    expect(container.read(authControllerProvider).isSignedIn, isFalse);
  });

  test('Dio sends JWT only to the configured API origin', () async {
    final container = ProviderContainer(
      overrides: [
        apiBaseUrlProvider.overrideWithValue('https://api.chiwawa.test'),
      ],
    );
    addTearDown(container.dispose);
    container.read(authTokenProvider.notifier).state = 'private-jwt';
    final dio = container.read(dioClientProvider);
    final adapter = RecordingHttpClientAdapter();
    dio.httpClientAdapter = adapter;

    await dio.get<void>('/api/v1/auth/me');
    await dio.get<void>('https://images.example.test/trip/photo.jpg');

    expect(
      adapter.requests.first.headers['Authorization'],
      'Bearer private-jwt',
    );
    expect(
      adapter.requests.last.headers.containsKey('Authorization'),
      isFalse,
    );
  });

  test('saved places use place id before display name for identity', () {
    final notifier = SavedPhotoPlacesNotifier();
    const first = PhotoSearchResult(
      id: 'place-a',
      name: '중앙 공원',
      address: '도쿄 치요다구',
      category: '공원',
    );
    const sameNameDifferentPlace = PhotoSearchResult(
      id: 'place-b',
      name: '중앙 공원',
      address: '오사카 주오구',
      category: '공원',
    );
    const renamedSamePlace = PhotoSearchResult(
      id: 'place-a',
      name: 'Central Park',
      address: '도쿄 치요다구',
      category: '공원',
    );

    expect(notifier.addPlace(first), isTrue);
    expect(notifier.addPlace(sameNameDifferentPlace), isTrue);
    expect(notifier.addPlace(renamedSamePlace), isFalse);
    expect(notifier.state, hasLength(2));
  });

  test('rapid auth changes persist the newest state', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final controller = container.read(authControllerProvider.notifier);

    final signingIn = controller.signInWithToken(
      'temporary-token',
      user: const AuthUser(
        name: '여행자',
        email: 'traveler@example.com',
      ),
    );
    final signingOut = controller.signOut();
    await Future.wait([signingIn, signingOut]);

    final prefs = await SharedPreferences.getInstance();
    expect(container.read(authControllerProvider).status, AuthStatus.signedOut);
    expect(prefs.getString('auth_status'), isNull);
    expect(prefs.getString('auth_token'), isNull);
    expect(prefs.getString('auth_user_email'), isNull);
  });

  test('sign out clears session-scoped frontend data', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final auth = container.read(authControllerProvider.notifier);
    await auth.continueAsGuest();

    container.read(savedPhotoPlacesProvider.notifier).addPlace(
          const PhotoSearchResult(
            id: 'saved-place',
            name: '저장 장소',
            address: '도쿄',
            category: '명소',
          ),
        );
    container.read(confirmedRouteProvider.notifier).confirm(
      const [
        RoutePlace(
          name: '확정 장소',
          duration: '30분',
          transport: '도보',
          category: '명소',
        ),
      ],
    );
    expect(container.read(savedPhotoPlacesProvider), hasLength(1));
    expect(container.read(confirmedRouteProvider), hasLength(1));

    await auth.signOut();

    expect(container.read(savedPhotoPlacesProvider), isEmpty);
    expect(container.read(confirmedRouteProvider), isEmpty);
  });

  test('ApiPlanRepository forwards the selected transport mode', () async {
    SharedPreferences.setMockInitialValues({});
    final tripIdStore = TripIdStore();
    await tripIdStore.save('trip-transport-test');
    final dio = Dio();
    final adapter = RecordingHttpClientAdapter();
    dio.httpClientAdapter = adapter;
    final repository = ApiPlanRepository(
      dio: dio,
      tripIdStore: tripIdStore,
    );

    await repository.optimizeRoute(
      const ['장소 A', '장소 B'],
      const TravelPreference(),
      TransportMode.drive,
    );

    expect(adapter.requests, hasLength(1));
    expect(
      adapter.requests.single.data,
      containsPair('transport_mode', 'drive'),
    );
  });
}

class SocketExceptionStub implements Exception {
  const SocketExceptionStub();
}

class RecordingHttpClientAdapter implements HttpClientAdapter {
  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return ResponseBody.fromString(
      '{}',
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
