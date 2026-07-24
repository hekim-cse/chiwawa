import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../env.dart';
import '../models/place_search_models.dart';
import '../services/trip_session_service.dart';
import 'api/api_place_search_repository.dart';

final placeSearchRepositoryProvider = Provider<PlaceSearchRepository>((ref) {
  ref.watch(authSessionRevisionProvider);
  ref.watch(currentTripRevisionProvider);
  if (useApiBackend) {
    return const ApiPlaceSearchRepository();
  }
  return const MockPlaceSearchRepository();
});

abstract class PlaceSearchRepository {
  Future<List<PlaceSearchCandidate>> searchPlaces(
    String query, {
    String? cityBias,
  });
}

class PlaceSearchException implements Exception {
  const PlaceSearchException(this.message);

  final String message;

  @override
  String toString() => message;
}

class MockPlaceSearchRepository implements PlaceSearchRepository {
  const MockPlaceSearchRepository();

  static const _places = <_MockPlaceEntry>[
    _MockPlaceEntry(
      candidate: PlaceSearchCandidate(
        providerPlaceId: 'mock-google-hotel-shinjuku',
        name: '신주쿠 그랜드 호텔',
        formattedAddress: '도쿄도 신주쿠구 니시신주쿠 2-7-2',
        latitude: 35.6896,
        longitude: 139.6917,
      ),
      keywords: ['숙소', '호텔', '신주쿠', '도쿄'],
    ),
    _MockPlaceEntry(
      candidate: PlaceSearchCandidate(
        providerPlaceId: 'mock-google-tokyo-station',
        name: '도쿄역',
        formattedAddress: '도쿄도 지요다구 마루노우치 1-9-1',
        latitude: 35.6812,
        longitude: 139.7671,
      ),
      keywords: ['도쿄', '도쿄역', '역', '마루노우치'],
    ),
    _MockPlaceEntry(
      candidate: PlaceSearchCandidate(
        providerPlaceId: 'mock-google-haneda-airport',
        name: '하네다 공항',
        formattedAddress: '도쿄도 오타구 하네다쿠코',
        latitude: 35.5494,
        longitude: 139.7798,
      ),
      keywords: ['하네다', '공항', '도쿄'],
    ),
    _MockPlaceEntry(
      candidate: PlaceSearchCandidate(
        providerPlaceId: 'mock-google-narita-airport',
        name: '나리타 국제공항',
        formattedAddress: '지바현 나리타시 후루고메 1-1',
        latitude: 35.7720,
        longitude: 140.3929,
      ),
      keywords: ['나리타', '공항', '도쿄'],
    ),
    _MockPlaceEntry(
      candidate: PlaceSearchCandidate(
        providerPlaceId: 'mock-google-asakusa-view-hotel',
        name: '아사쿠사 뷰 호텔',
        formattedAddress: '도쿄도 다이토구 니시아사쿠사 3-17-1',
        latitude: 35.7148,
        longitude: 139.7934,
      ),
      keywords: ['숙소', '호텔', '아사쿠사', '도쿄'],
    ),
  ];

  @override
  Future<List<PlaceSearchCandidate>> searchPlaces(
    String query, {
    String? cityBias,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 220));
    final normalized = query.trim().toLowerCase();
    if (normalized.isEmpty) return const [];

    final results = [
      for (final entry in _places)
        if (entry.matches(normalized)) entry.candidate,
    ];
    return List<PlaceSearchCandidate>.unmodifiable(results.take(5));
  }
}

class _MockPlaceEntry {
  const _MockPlaceEntry({
    required this.candidate,
    required this.keywords,
  });

  final PlaceSearchCandidate candidate;
  final List<String> keywords;

  bool matches(String query) {
    return candidate.name.toLowerCase().contains(query) ||
        candidate.formattedAddress.toLowerCase().contains(query) ||
        keywords.any((keyword) => keyword.toLowerCase().contains(query));
  }
}
