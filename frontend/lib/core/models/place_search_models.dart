class PlaceSearchCandidate {
  const PlaceSearchCandidate({
    required this.providerPlaceId,
    required this.name,
    required this.formattedAddress,
    required this.latitude,
    required this.longitude,
  });

  final String providerPlaceId;
  final String name;
  final String formattedAddress;
  final double latitude;
  final double longitude;

  bool get isValid =>
      providerPlaceId.trim().isNotEmpty &&
      name.trim().isNotEmpty &&
      latitude >= -90 &&
      latitude <= 90 &&
      longitude >= -180 &&
      longitude <= 180;

  @override
  bool operator ==(Object other) {
    return other is PlaceSearchCandidate &&
        other.providerPlaceId == providerPlaceId;
  }

  @override
  int get hashCode => providerPlaceId.hashCode;
}
