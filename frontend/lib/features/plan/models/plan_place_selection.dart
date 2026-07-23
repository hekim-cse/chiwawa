import '../../../core/models/travel_models.dart';

enum PlanPlaceSource { seed, manual, photoSearch, freeTime }

class PlanPlaceSelection {
  const PlanPlaceSelection({
    required this.id,
    required this.name,
    required this.source,
    this.address = '',
    this.serverPlaceId,
    this.latitude,
    this.longitude,
  });

  factory PlanPlaceSelection.fromPhoto(PhotoSearchResult place) {
    return PlanPlaceSelection(
      id: photoIdentity(place),
      name: place.name,
      address: place.address,
      source: PlanPlaceSource.photoSearch,
      serverPlaceId: place.wantedPlaceId.isEmpty ? null : place.wantedPlaceId,
      latitude: place.latitude,
      longitude: place.longitude,
    );
  }

  final String id;
  final String name;
  final String address;
  final PlanPlaceSource source;
  final String? serverPlaceId;
  final double? latitude;
  final double? longitude;

  bool get isPersisted => serverPlaceId?.trim().isNotEmpty ?? false;

  PlanPlaceSelection copyWith({String? serverPlaceId}) {
    return PlanPlaceSelection(
      id: id,
      name: name,
      address: address,
      source: source,
      serverPlaceId: serverPlaceId ?? this.serverPlaceId,
      latitude: latitude,
      longitude: longitude,
    );
  }

  static String photoIdentity(PhotoSearchResult place) {
    return 'photo:${place.identityKey}';
  }

  @override
  bool operator ==(Object other) {
    return other is PlanPlaceSelection && other.id == id;
  }

  @override
  int get hashCode => id.hashCode;
}
