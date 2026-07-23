import 'transport_mode.dart';
import 'travel_models.dart';

class PlanRoutePlaceInput {
  const PlanRoutePlaceInput({
    required this.localId,
    required this.name,
    this.serverPlaceId,
    this.address = '',
    this.latitude,
    this.longitude,
  });

  final String localId;
  final String? serverPlaceId;
  final String name;
  final String address;
  final double? latitude;
  final double? longitude;

  bool get isPersisted => serverPlaceId?.trim().isNotEmpty ?? false;
}

class WantedPlaceRecord {
  const WantedPlaceRecord({
    required this.id,
    required this.name,
    this.address = '',
    this.latitude,
    this.longitude,
  });

  final String id;
  final String name;
  final String address;
  final double? latitude;
  final double? longitude;

  factory WantedPlaceRecord.fromJson(Map<String, Object?> json) {
    final city = json['city'] as String? ?? '';
    final country = json['country'] as String? ?? '';
    return WantedPlaceRecord(
      id: json['id']?.toString() ?? '',
      name: json['name'] as String? ?? '',
      address:
          [city, country].where((part) => part.trim().isNotEmpty).join(', '),
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
    );
  }
}

class RouteOptimizationRequest {
  const RouteOptimizationRequest({
    required this.places,
    required this.preference,
    required this.transportMode,
    required this.dayIndex,
    required this.plannedStartTime,
    required this.plannedEndTime,
    required this.maxPlaceCount,
  });

  final List<PlanRoutePlaceInput> places;
  final TravelPreference preference;
  final TransportMode transportMode;
  final int dayIndex;
  final String plannedStartTime;
  final String plannedEndTime;
  final int maxPlaceCount;

  List<String> get wantedPlaceIds => [
        for (final place in places)
          if (place.isPersisted) place.serverPlaceId!,
      ];
}
