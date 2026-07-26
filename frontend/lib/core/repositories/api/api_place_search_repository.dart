import 'package:dio/dio.dart';

import '../../api/api_exception.dart';
import '../../models/place_search_models.dart';
import '../place_search_repository.dart';

/// Backend를 통해 Google Places Text Search를 호출하는 구현체.
class ApiPlaceSearchRepository implements PlaceSearchRepository {
  const ApiPlaceSearchRepository({required this.dio});

  final Dio dio;

  @override
  Future<List<PlaceSearchCandidate>> searchPlaces(
    String query, {
    String? cityBias,
  }) async {
    final normalizedQuery = query.trim();
    if (normalizedQuery.isEmpty) return const [];
    try {
      final response = await dio.get<Map<String, Object?>>(
        '/api/v1/places/search',
        queryParameters: {
          'query': normalizedQuery,
          if (cityBias?.trim().isNotEmpty ?? false)
            'city_bias': cityBias!.trim(),
        },
      );
      final items = response.data?['items'] as List<Object?>? ?? const [];
      return List<PlaceSearchCandidate>.unmodifiable([
        for (final item in items)
          _candidateFromJson(Map<String, Object?>.from(item! as Map)),
      ]);
    } on DioException catch (error) {
      throw PlaceSearchException(mapApiErrorToMessage(error));
    }
  }

  PlaceSearchCandidate _candidateFromJson(Map<String, Object?> json) {
    final providerPlaceId = json['provider_place_id'];
    final name = json['name'];
    final formattedAddress = json['formatted_address'];
    final latitude = json['latitude'];
    final longitude = json['longitude'];
    if (providerPlaceId is! String ||
        providerPlaceId.trim().isEmpty ||
        name is! String ||
        name.trim().isEmpty ||
        formattedAddress is! String ||
        formattedAddress.trim().isEmpty ||
        latitude is! num ||
        longitude is! num) {
      throw const PlaceSearchException('장소 검색 응답 형식이 올바르지 않아요.');
    }
    return PlaceSearchCandidate(
      providerPlaceId: providerPlaceId,
      name: name,
      formattedAddress: formattedAddress,
      latitude: latitude.toDouble(),
      longitude: longitude.toDouble(),
    );
  }
}
