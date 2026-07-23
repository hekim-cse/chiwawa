import 'dart:convert';
import 'dart:typed_data';

import 'package:chiwawa/core/models/photo_upload.dart';
import 'package:chiwawa/core/repositories/api/api_photo_place_repository.dart';
import 'package:chiwawa/core/services/trip_session_service.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
  });

  test('photo search uploads the actual file and preserves confirmed server id',
      () async {
    final store = TripIdStore();
    await store.save('trip-photo-contract');
    final dio = Dio();
    final adapter = _QueueHttpClientAdapter([
      {
        'id': 'photo-search-1',
        'candidates': [
          {
            'id': 'candidate-1',
            'name': '아사쿠사 센소지',
            'city': '도쿄',
            'country': '일본',
            'latitude': 35.7148,
            'longitude': 139.7967,
            'confidence': 0.94,
          },
        ],
      },
      {
        'wanted_place': {'id': 'wanted-place-1'},
      },
    ]);
    dio.httpClientAdapter = adapter;
    final repository = ApiPhotoPlaceRepository(
      dio: dio,
      tripIdStore: store,
    );

    final candidates = await repository.analyzePhotoCandidates(
      PhotoUpload(
        bytes: Uint8List.fromList(const [0x89, 0x50, 0x4e, 0x47]),
        fileName: 'trip-photo.png',
        mimeType: 'image/png',
        previewPath: 'blob:trip-photo',
      ),
    );
    final confirmed = await repository.confirmPhotoPlace(candidates.single);

    expect(adapter.requests, hasLength(2));
    expect(
      adapter.requests.first.path,
      '/api/v1/trips/trip-photo-contract/photo-places/search',
    );
    final formData = adapter.requests.first.data as FormData;
    expect(formData.fields, isEmpty);
    expect(formData.files.single.key, 'file');
    expect(formData.files.single.value.filename, 'trip-photo.png');
    expect(
      formData.files.single.value.contentType?.toString(),
      'image/png',
    );
    expect(candidates.single.searchId, 'photo-search-1');
    expect(candidates.single.imagePath, 'blob:trip-photo');
    expect(
      adapter.requests.last.path,
      '/api/v1/trips/trip-photo-contract/photo-places/'
      'photo-search-1/confirm',
    );
    expect(
      adapter.requests.last.data,
      containsPair('candidate_id', 'candidate-1'),
    );
    expect(confirmed.wantedPlaceId, 'wanted-place-1');
  });
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
