import 'dart:typed_data';

import 'package:chiwawa/core/models/memorial_models.dart';
import 'package:chiwawa/core/providers/data_providers.dart';
import 'package:chiwawa/core/repositories/api/api_memorial_repository.dart';
import 'package:chiwawa/core/repositories/memorial_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Memorial models parse PR 41 calendar and nullable coordinates', () {
    final calendar = MemorialCalendar.fromJson(const {
      'year': 2026,
      'month': 7,
      'days': [
        {'day': '2026-07-01', 'photo_count': 2},
      ],
    });
    final timeline = MemorialDayTimeline.fromJson(const {
      'day': '2026-07-01',
      'items': [
        {
          'seq': 1,
          'photo': {
            'id': 13,
            'file_name': 'without-location.jpg',
            'content_type': 'image/jpeg',
            'taken_at': '2026-07-01T12:00:00+09:00',
            'latitude': null,
            'longitude': null,
            'address': null,
            'memo': null,
            'file_url': '/api/v1/memorial/photos/13/file',
            'created_at': '2026-07-09T02:12:00+00:00',
          },
        },
        {
          'seq': 0,
          'photo': {
            'id': 12,
            'file_name': 'dotonbori.jpg',
            'content_type': 'image/jpeg',
            'taken_at': '2026-07-01T10:30:00+09:00',
            'latitude': 34.6687,
            'longitude': 135.5031,
            'address': '일본 오사카부 오사카시',
            'memo': '점심',
            'file_url': '/api/v1/memorial/photos/12/file',
            'created_at': '2026-07-09T02:11:45+00:00',
          },
        },
      ],
    });

    expect(calendar.days.single.photoCount, 2);
    expect(timeline.items.first.seq, 0);
    expect(timeline.photoCount, 2);
    expect(timeline.locatedPhotoCount, 1);
    expect(timeline.unlocatedPhotoCount, 1);
    expect(timeline.items.last.photo.hasCoordinates, isFalse);
  });

  test('ApiMemorialRepository calls calendar day and authenticated file paths',
      () async {
    final interceptor = _MemorialApiInterceptor();
    final dio = Dio(BaseOptions(baseUrl: 'https://example.test'))
      ..interceptors.add(interceptor);
    final repository = ApiMemorialRepository(dio: dio);

    final calendar =
        await repository.fetchCalendar(const MemorialMonth(2026, 7));
    final timeline = await repository.fetchDay(DateTime(2026, 7, 1));
    final bytes = await repository.fetchPhotoBytes(
      '/api/v1/memorial/photos/12/file',
    );

    expect(calendar.days.single.photoCount, 1);
    expect(timeline.items.single.photo.id, '12');
    expect(bytes, Uint8List.fromList([1, 2, 3]));

    expect(interceptor.requests[0].path, '/api/v1/memorial/calendar');
    expect(interceptor.requests[0].queryParameters, {
      'year': 2026,
      'month': 7,
    });
    expect(interceptor.requests[1].path, '/api/v1/memorial/days/2026-07-01');
    expect(interceptor.requests[2].path, '/api/v1/memorial/photos/12/file');
    expect(interceptor.requests[2].responseType, ResponseType.bytes);
    expect(
      interceptor.requests[2].headers['Authorization'],
      'Bearer test-token',
    );
  });

  test('pawMapProvider excludes only photos without coordinates', () async {
    final date = DateTime(2026, 7, 1);
    final container = ProviderContainer(
      overrides: [
        memorialRepositoryProvider.overrideWithValue(
          _StaticMemorialRepository(date),
        ),
      ],
    );
    addTearDown(container.dispose);

    final timeline = await container.read(memorialDayProvider(date).future);
    final clusters = await container.read(pawMapProvider(date).future);

    expect(timeline.photoCount, 2);
    expect(timeline.unlocatedPhotoCount, 1);
    expect(clusters, hasLength(1));
    expect(clusters.single.photos.single.id, 'located');
  });

  test('MemorialMonth moves across year boundaries', () {
    expect(
        const MemorialMonth(2026, 1).previous, const MemorialMonth(2025, 12));
    expect(const MemorialMonth(2026, 12).next, const MemorialMonth(2027, 1));
  });
}

class _MemorialApiInterceptor extends Interceptor {
  final requests = <RequestOptions>[];

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.headers['Authorization'] = 'Bearer test-token';
    requests.add(options);

    final Object data;
    if (options.path.endsWith('/calendar')) {
      data = const {
        'year': 2026,
        'month': 7,
        'days': [
          {'day': '2026-07-01', 'photo_count': 1},
        ],
      };
    } else if (options.path.contains('/days/')) {
      data = const {
        'day': '2026-07-01',
        'items': [
          {
            'seq': 0,
            'photo': {
              'id': 12,
              'file_name': 'photo.jpg',
              'content_type': 'image/jpeg',
              'taken_at': '2026-07-01T10:30:00+09:00',
              'latitude': 34.6687,
              'longitude': 135.5031,
              'address': '도톤보리',
              'memo': null,
              'file_url': '/api/v1/memorial/photos/12/file',
              'created_at': '2026-07-09T02:11:45+00:00',
            },
          },
        ],
      };
    } else {
      data = <int>[1, 2, 3];
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

class _StaticMemorialRepository implements MemorialRepository {
  const _StaticMemorialRepository(this.date);

  final DateTime date;

  @override
  Future<MemorialCalendar> fetchCalendar(MemorialMonth month) async {
    return MemorialCalendar(
      year: month.year,
      month: month.month,
      days: [MemorialCalendarDay(day: date, photoCount: 2)],
    );
  }

  @override
  Future<MemorialDayTimeline> fetchDay(DateTime day) async {
    return MemorialDayTimeline(
      day: day,
      items: [
        MemorialTimelineEntry(
          seq: 0,
          photo: MemorialPhoto(
            id: 'located',
            fileName: 'located.jpg',
            contentType: 'image/jpeg',
            takenAt: DateTime(2026, 7, 1, 10),
            latitude: 34.6687,
            longitude: 135.5031,
            address: '도톤보리',
            fileUrl: '/api/v1/memorial/photos/1/file',
          ),
        ),
        MemorialTimelineEntry(
          seq: 1,
          photo: MemorialPhoto(
            id: 'unlocated',
            fileName: 'unlocated.jpg',
            contentType: 'image/jpeg',
            takenAt: DateTime(2026, 7, 1, 11),
            fileUrl: '/api/v1/memorial/photos/2/file',
          ),
        ),
      ],
    );
  }

  @override
  Future<MemorialOverview?> fetchOverview() async => null;

  @override
  Future<Uint8List> fetchPhotoBytes(String fileUrl) async => Uint8List(0);
}
