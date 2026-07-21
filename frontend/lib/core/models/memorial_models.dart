import 'travel_models.dart';

class MemorialMonth {
  const MemorialMonth(this.year, this.month)
      : assert(month >= 1 && month <= 12);

  factory MemorialMonth.fromDate(DateTime date) {
    return MemorialMonth(date.year, date.month);
  }

  final int year;
  final int month;

  MemorialMonth get previous {
    final date = DateTime(year, month - 1);
    return MemorialMonth(date.year, date.month);
  }

  MemorialMonth get next {
    final date = DateTime(year, month + 1);
    return MemorialMonth(date.year, date.month);
  }

  DateTime get firstDay => DateTime(year, month);

  @override
  bool operator ==(Object other) {
    return other is MemorialMonth && other.year == year && other.month == month;
  }

  @override
  int get hashCode => Object.hash(year, month);
}

class MemorialPhoto {
  const MemorialPhoto({
    required this.id,
    required this.fileName,
    required this.contentType,
    required this.takenAt,
    required this.fileUrl,
    this.latitude,
    this.longitude,
    this.address,
    this.memo,
    this.createdAt,
    this.assetPath = '',
  });

  final String id;
  final String fileName;
  final String contentType;
  final DateTime takenAt;
  final double? latitude;
  final double? longitude;
  final String? address;
  final String? memo;
  final String fileUrl;
  final DateTime? createdAt;

  /// Mock 전용 로컬 asset. API 응답에서는 빈 문자열이다.
  final String assetPath;

  bool get hasCoordinates => latitude != null && longitude != null;

  factory MemorialPhoto.fromJson(Map<String, Object?> json) {
    final takenAt = json['taken_at'] as String?;
    if (takenAt == null || takenAt.isEmpty) {
      throw const FormatException('Memorial photo requires taken_at.');
    }

    final createdAt = json['created_at'] as String?;
    return MemorialPhoto(
      id: json['id']?.toString() ?? '',
      fileName: json['file_name'] as String? ?? '',
      contentType: json['content_type'] as String? ?? 'image/jpeg',
      takenAt: DateTime.parse(takenAt),
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      address: json['address'] as String?,
      memo: json['memo'] as String?,
      fileUrl: json['file_url'] as String? ?? '',
      createdAt: createdAt == null || createdAt.isEmpty
          ? null
          : DateTime.parse(createdAt),
      assetPath: json['asset_path'] as String? ?? '',
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'file_name': fileName,
      'content_type': contentType,
      'taken_at': takenAt.toIso8601String(),
      'latitude': latitude,
      'longitude': longitude,
      'address': address,
      'memo': memo,
      'file_url': fileUrl,
      'created_at': createdAt?.toIso8601String(),
      if (assetPath.isNotEmpty) 'asset_path': assetPath,
    };
  }
}

class MemorialCalendarDay {
  const MemorialCalendarDay({required this.day, required this.photoCount});

  final DateTime day;
  final int photoCount;

  factory MemorialCalendarDay.fromJson(Map<String, Object?> json) {
    final day = json['day'] as String?;
    if (day == null || day.isEmpty) {
      throw const FormatException('Memorial calendar day requires day.');
    }
    return MemorialCalendarDay(
      day: DateTime.parse(day),
      photoCount: (json['photo_count'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'day': _formatDate(day),
      'photo_count': photoCount,
    };
  }
}

class MemorialCalendar {
  const MemorialCalendar({
    required this.year,
    required this.month,
    required this.days,
  });

  final int year;
  final int month;
  final List<MemorialCalendarDay> days;

  factory MemorialCalendar.fromJson(Map<String, Object?> json) {
    final rawDays = json['days'] as List<Object?>? ?? const [];
    return MemorialCalendar(
      year: (json['year'] as num?)?.toInt() ?? 0,
      month: (json['month'] as num?)?.toInt() ?? 0,
      days: List.unmodifiable(
        rawDays.map((raw) => MemorialCalendarDay.fromJson(_asMap(raw))),
      ),
    );
  }
}

class MemorialTimelineEntry {
  const MemorialTimelineEntry({required this.seq, required this.photo});

  final int seq;
  final MemorialPhoto photo;

  factory MemorialTimelineEntry.fromJson(Map<String, Object?> json) {
    return MemorialTimelineEntry(
      seq: (json['seq'] as num?)?.toInt() ?? 0,
      photo: MemorialPhoto.fromJson(_asMap(json['photo'])),
    );
  }
}

class MemorialDayTimeline {
  const MemorialDayTimeline({required this.day, required this.items});

  final DateTime day;
  final List<MemorialTimelineEntry> items;

  int get photoCount => items.length;
  int get locatedPhotoCount =>
      items.where((entry) => entry.photo.hasCoordinates).length;
  int get unlocatedPhotoCount => photoCount - locatedPhotoCount;

  factory MemorialDayTimeline.fromJson(Map<String, Object?> json) {
    final rawDay = json['day'] as String?;
    if (rawDay == null || rawDay.isEmpty) {
      throw const FormatException('Memorial day timeline requires day.');
    }
    final rawItems = json['items'] as List<Object?>? ?? const [];
    final items = rawItems
        .map((raw) => MemorialTimelineEntry.fromJson(_asMap(raw)))
        .toList()
      ..sort((a, b) => a.seq.compareTo(b.seq));
    return MemorialDayTimeline(
      day: DateTime.parse(rawDay),
      items: List.unmodifiable(items),
    );
  }
}

class MemorialOverview {
  const MemorialOverview({
    required this.tripInfo,
    required this.summary,
    required this.days,
  });

  final TripInfo tripInfo;
  final MemorialSummary summary;
  final List<MemorialDay> days;
}

Map<String, Object?> _asMap(Object? value) {
  if (value is Map<String, Object?>) return value;
  if (value is Map) return Map<String, Object?>.from(value);
  throw const FormatException('Expected a JSON object.');
}

String _formatDate(DateTime date) {
  final month = date.month.toString().padLeft(2, '0');
  final day = date.day.toString().padLeft(2, '0');
  return '${date.year}-$month-$day';
}

bool isSameMemorialDay(DateTime a, DateTime b) {
  return a.year == b.year && a.month == b.month && a.day == b.day;
}
