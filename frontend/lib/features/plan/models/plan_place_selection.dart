import '../../../core/models/travel_models.dart';

enum PlanPlaceSource { seed, manual, photoSearch, freeTime }

class PlanPlaceSelection {
  const PlanPlaceSelection({
    required this.id,
    required this.name,
    required this.source,
    this.address = '',
  });

  factory PlanPlaceSelection.fromPhoto(PhotoSearchResult place) {
    return PlanPlaceSelection(
      id: photoIdentity(place),
      name: place.name,
      address: place.address,
      source: PlanPlaceSource.photoSearch,
    );
  }

  final String id;
  final String name;
  final String address;
  final PlanPlaceSource source;

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
