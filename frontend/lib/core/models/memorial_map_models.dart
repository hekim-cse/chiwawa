class MemorialPhotoPoint {
  const MemorialPhotoPoint({
    required this.id,
    required this.takenAt,
    required this.latitude,
    required this.longitude,
    required this.placeName,
    required this.assetPath,
  });

  final String id;
  final DateTime takenAt;
  final double latitude;
  final double longitude;
  final String placeName;
  final String assetPath;

  factory MemorialPhotoPoint.fromJson(Map<String, Object?> json) {
    final latitude = (json['latitude'] as num?)?.toDouble();
    final longitude = (json['longitude'] as num?)?.toDouble();
    final takenAt = json['taken_at'] as String?;

    if (latitude == null || longitude == null) {
      throw const FormatException('Memorial photo point requires coordinates.');
    }
    if (takenAt == null || takenAt.isEmpty) {
      throw const FormatException('Memorial photo point requires taken_at.');
    }

    return MemorialPhotoPoint(
      id: json['id']?.toString() ?? '',
      takenAt: DateTime.parse(takenAt),
      latitude: latitude,
      longitude: longitude,
      placeName: json['place_name'] as String? ?? '',
      assetPath: json['asset_path'] as String? ?? '',
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'taken_at': takenAt.toIso8601String(),
      'latitude': latitude,
      'longitude': longitude,
      'place_name': placeName,
      'asset_path': assetPath,
    };
  }
}

class PawCluster {
  const PawCluster({
    required this.id,
    required this.placeName,
    required this.latitude,
    required this.longitude,
    required this.arrivalTime,
    required this.photos,
  });

  final String id;
  final String placeName;
  final double latitude;
  final double longitude;
  final DateTime arrivalTime;
  final List<MemorialPhotoPoint> photos;

  int get photoCount => photos.length;
}
