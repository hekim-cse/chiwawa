import '../utils/time_formatters.dart';

enum ScheduleStatus { completed, ongoing, free, upcoming }

enum AiJobStatus { idle, pending, running, done, failed }

enum TravelTheme { photoSpot, culture, food, shopping }

enum TravelPace { relaxed, balanced, packed }

extension TravelThemeLabel on TravelTheme {
  String get label {
    return switch (this) {
      TravelTheme.photoSpot => '포토스팟',
      TravelTheme.culture => '문화·역사',
      TravelTheme.food => '맛집',
      TravelTheme.shopping => '쇼핑',
    };
  }

  String get code {
    return switch (this) {
      TravelTheme.photoSpot => 'photo_spot',
      TravelTheme.culture => 'culture',
      TravelTheme.food => 'food',
      TravelTheme.shopping => 'shopping',
    };
  }

  static TravelTheme fromCode(String code) {
    return TravelTheme.values.firstWhere(
      (theme) => theme.code == code,
      orElse: () => TravelTheme.photoSpot,
    );
  }
}

extension TravelPaceLabel on TravelPace {
  String get label {
    return switch (this) {
      TravelPace.relaxed => '여유롭게',
      TravelPace.balanced => '적당히',
      TravelPace.packed => '알차게',
    };
  }

  String get code {
    return switch (this) {
      TravelPace.relaxed => 'relaxed',
      TravelPace.balanced => 'balanced',
      TravelPace.packed => 'packed',
    };
  }

  static TravelPace fromCode(String code) {
    return TravelPace.values.firstWhere(
      (pace) => pace.code == code,
      orElse: () => TravelPace.balanced,
    );
  }
}

class TravelPreference {
  const TravelPreference({
    this.themes = const {TravelTheme.photoSpot, TravelTheme.culture},
    this.pace = TravelPace.balanced,
  });

  final Set<TravelTheme> themes;
  final TravelPace pace;

  TravelPreference copyWith({
    Set<TravelTheme>? themes,
    TravelPace? pace,
  }) {
    return TravelPreference(
      themes: themes ?? this.themes,
      pace: pace ?? this.pace,
    );
  }

  factory TravelPreference.fromJson(Map<String, Object?> json) {
    final rawThemes = json['themes'];
    return TravelPreference(
      themes: rawThemes is List
          ? rawThemes.whereType<String>().map(TravelThemeLabel.fromCode).toSet()
          : const {TravelTheme.photoSpot, TravelTheme.culture},
      pace: TravelPaceLabel.fromCode(json['pace'] as String? ?? ''),
    );
  }

  Map<String, Object?> toJson() {
    return {
      'themes': themes.map((theme) => theme.code).toList(),
      'pace': pace.code,
    };
  }
}

class Trip {
  const Trip({
    required this.id,
    required this.title,
    required this.city,
    required this.country,
    required this.startDate,
    required this.endDate,
    required this.travelers,
    required this.interests,
    required this.travelStyle,
  });

  final String id;
  final String title;
  final String city;
  final String country;
  final String startDate;
  final String endDate;
  final int travelers;
  final List<String> interests;
  final TravelPace travelStyle;

  factory Trip.fromJson(Map<String, Object?> json) {
    final rawInterests = json['interests'];
    return Trip(
      id: json['id']?.toString() ?? '',
      title: json['title'] as String? ?? '여행',
      city: json['city'] as String? ?? '',
      country: json['country'] as String? ?? 'Japan',
      startDate: json['start_date'] as String? ?? '',
      endDate: json['end_date'] as String? ?? '',
      travelers: (json['travelers'] as num?)?.toInt() ?? 1,
      interests: rawInterests is List
          ? rawInterests.whereType<String>().toList(growable: false)
          : const [],
      travelStyle:
          TravelPaceLabel.fromCode(json['travel_style'] as String? ?? ''),
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'title': title,
      'city': city,
      'country': country,
      'start_date': startDate,
      'end_date': endDate,
      'travelers': travelers,
      'interests': interests,
      'travel_style': travelStyle.code,
    };
  }

  TripInfo toTripInfo({DateTime? today}) {
    final cityLabel = country.isEmpty ? city : '$city, $country';
    return TripInfo(
      tripId: id,
      tripName: title,
      period: '$startDate ~ $endDate',
      currentDay: _currentDayLabel(today ?? DateTime.now()),
      members: travelers,
      city: cityLabel,
      weather: '',
    );
  }

  String _currentDayLabel(DateTime today) {
    final start = DateTime.tryParse(startDate);
    final end = DateTime.tryParse(endDate);
    if (start == null || end == null) return '';

    final date = DateTime(today.year, today.month, today.day);
    final firstDay = DateTime(start.year, start.month, start.day);
    final lastDay = DateTime(end.year, end.month, end.day);
    if (date.isBefore(firstDay)) return '여행 전';
    if (date.isAfter(lastDay)) return '여행 완료';
    return '${date.difference(firstDay).inDays + 1}일차';
  }
}

class TripDraft {
  const TripDraft({
    required this.city,
    this.country = 'Japan',
    required this.startDate,
    required this.endDate,
    this.travelers = 1,
    this.interests = const [],
    this.travelStyle = TravelPace.balanced,
    this.title,
  });

  final String city;
  final String country;
  final String startDate;
  final String endDate;
  final int travelers;
  final List<String> interests;
  final TravelPace travelStyle;
  final String? title;

  Map<String, Object?> toJson() {
    return {
      'city': city,
      'country': country,
      'start_date': startDate,
      'end_date': endDate,
      'travelers': travelers,
      'interests': interests,
      'travel_style': travelStyle.code,
      if (title != null && title!.trim().isNotEmpty) 'title': title!.trim(),
    };
  }
}

class TripInfo {
  const TripInfo({
    required this.tripId,
    required this.tripName,
    required this.period,
    required this.currentDay,
    required this.members,
    required this.city,
    required this.weather,
  });

  final String tripId;
  final String tripName;
  final String period;
  final String currentDay;
  final int members;
  final String city;
  final String weather;

  factory TripInfo.fromJson(Map<String, Object?> json) {
    final startDate = json['start_date'] as String?;
    final endDate = json['end_date'] as String?;

    return TripInfo(
      tripId: json['trip_id'] as String? ?? json['id'] as String? ?? '',
      tripName: json['trip_name'] as String? ??
          json['name'] as String? ??
          json['title'] as String? ??
          '여행',
      period: json['period'] as String? ??
          (startDate != null && endDate != null ? '$startDate ~ $endDate' : ''),
      currentDay: json['current_day']?.toString() ?? '',
      members: json['members'] as int? ?? json['travelers'] as int? ?? 1,
      city: json['city'] as String? ?? '',
      weather: json['weather'] as String? ??
          json['weather_summary'] as String? ??
          '',
    );
  }

  Map<String, Object?> toJson() {
    return {
      'trip_id': tripId,
      'trip_name': tripName,
      'period': period,
      'current_day': currentDay,
      'members': members,
      'city': city,
      'weather': weather,
    };
  }
}

class ScheduleItem {
  const ScheduleItem({
    required this.id,
    required this.tripId,
    required this.date,
    required this.startTime,
    this.endTime,
    this.name,
    this.placeId,
    this.notes,
    required this.source,
    this.transport = '',
    this.freeMinutes,
    this.status = ScheduleStatus.upcoming,
  });

  final String id;
  final String tripId;
  final String date;
  final String startTime;
  final String? endTime;
  final String? name;
  final String? placeId;
  final String? notes;
  final String source;

  // TODO(A1): transport/status are frontend display fields until the backend
  // confirms whether these fields are included in schedule responses.
  final String transport;
  final int? freeMinutes;
  final ScheduleStatus status;

  String get time => formatTime(startTime);
  String? get place => name;

  factory ScheduleItem.fromJson(Map<String, Object?> json) {
    return ScheduleItem(
      id: json['id']?.toString() ?? '',
      tripId: json['trip_id']?.toString() ?? '',
      date: json['date'] as String? ?? '',
      startTime: json['start_time'] as String? ?? json['time'] as String? ?? '',
      endTime: json['end_time'] as String?,
      name: json['name'] as String? ?? json['place'] as String?,
      placeId: json['place_id']?.toString(),
      notes: json['notes'] as String?,
      source: json['source'] as String? ?? 'mock',
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'trip_id': tripId,
      'name': name,
      'date': date,
      'start_time': startTime,
      'end_time': endTime,
      'place_id': placeId,
      'notes': notes,
      'source': source,
    };
  }
}

extension ScheduleItemIdentity on ScheduleItem {
  String get identityKey {
    final normalizedId = id.trim();
    if (normalizedId.isNotEmpty) return normalizedId;
    return [tripId, date, startTime, placeId ?? '', name ?? ''].join('|');
  }
}

class RoutePlace {
  const RoutePlace({
    required this.name,
    required this.duration,
    required this.transport,
    required this.category,
    this.travelCost = '',
  });

  final String name;
  final String duration;
  final String transport;
  final String category;
  final String travelCost;

  factory RoutePlace.fromJson(Map<String, Object?> json) {
    return RoutePlace(
      name: json['name'] as String? ?? '',
      duration: json['duration'] as String? ??
          '${json['stay_minutes'] ?? json['expected_stay_minutes'] ?? ''}분',
      transport: json['transport'] as String? ??
          json['transport_from_previous'] as String? ??
          '',
      category: json['category'] as String? ?? '',
      travelCost:
          json['travel_cost']?.toString() ?? json['cost']?.toString() ?? '',
    );
  }

  Map<String, Object?> toJson() {
    return {
      'name': name,
      'duration': duration,
      'transport': transport,
      'category': category,
      'travel_cost': travelCost,
    };
  }
}

extension RoutePlaceIdentity on RoutePlace {
  String get identityKey =>
      [name, duration, transport, category, travelCost].join('|');
}

class RouteOptimizationState {
  const RouteOptimizationState({
    required this.status,
    this.places = const [],
    this.message,
  });

  const RouteOptimizationState.idle()
      : status = AiJobStatus.idle,
        places = const [],
        message = null;

  const RouteOptimizationState.pending()
      : status = AiJobStatus.pending,
        places = const [],
        message = null;

  const RouteOptimizationState.running()
      : status = AiJobStatus.running,
        places = const [],
        message = null;

  const RouteOptimizationState.done(List<RoutePlace> routePlaces)
      : status = AiJobStatus.done,
        places = routePlaces,
        message = null;

  const RouteOptimizationState.failed(String failureMessage)
      : status = AiJobStatus.failed,
        places = const [],
        message = failureMessage;

  final AiJobStatus status;
  final List<RoutePlace> places;
  final String? message;

  bool get isWorking =>
      status == AiJobStatus.pending || status == AiJobStatus.running;
}

class FreeTimeRecommend {
  const FreeTimeRecommend({
    required this.name,
    required this.walk,
    required this.duration,
  });

  final String name;
  final String walk;
  final String duration;

  factory FreeTimeRecommend.fromJson(Map<String, Object?> json) {
    return FreeTimeRecommend(
      name: json['title'] as String? ?? json['name'] as String? ?? '',
      walk: json['walk'] as String? ?? '',
      duration:
          json['duration'] as String? ?? '${json['duration_minutes'] ?? ''}분',
    );
  }

  Map<String, Object?> toJson() {
    return {
      'name': name,
      'walk': walk,
      'duration': duration,
    };
  }
}

class PhotoSearchResult {
  const PhotoSearchResult({
    this.id = '',
    required this.name,
    required this.address,
    required this.category,
    this.latitude,
    this.longitude,
    this.confidence,
    this.imagePath,
  });

  final String id;
  final String name;
  final String address;
  final String category;
  final double? latitude;
  final double? longitude;
  final double? confidence;
  final String? imagePath;

  PhotoSearchResult copyWith({
    String? id,
    String? name,
    String? address,
    String? category,
    double? latitude,
    double? longitude,
    double? confidence,
    String? imagePath,
  }) {
    return PhotoSearchResult(
      id: id ?? this.id,
      name: name ?? this.name,
      address: address ?? this.address,
      category: category ?? this.category,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      confidence: confidence ?? this.confidence,
      imagePath: imagePath ?? this.imagePath,
    );
  }

  factory PhotoSearchResult.fromJson(Map<String, Object?> json) {
    return PhotoSearchResult(
      id: json['place_id']?.toString() ?? json['id']?.toString() ?? '',
      name: json['name'] as String? ?? '',
      address: json['address'] as String? ?? '',
      category: json['category'] as String? ?? '',
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      confidence: (json['confidence'] as num?)?.toDouble(),
      imagePath: json['image_url'] as String? ?? json['image_path'] as String?,
    );
  }

  Map<String, Object?> toJson() {
    return {
      'place_id': id,
      'name': name,
      'address': address,
      'category': category,
      'latitude': latitude,
      'longitude': longitude,
      'confidence': confidence,
      'image_path': imagePath,
    };
  }
}

extension PhotoSearchResultIdentity on PhotoSearchResult {
  String get identityKey {
    final normalizedId = id.trim();
    if (normalizedId.isNotEmpty) return normalizedId;
    return [
      _normalizePlaceIdentity(name),
      _normalizePlaceIdentity(address),
      latitude?.toStringAsFixed(6) ?? '',
      longitude?.toStringAsFixed(6) ?? '',
    ].join('|');
  }

  bool hasSameIdentityAs(PhotoSearchResult other) {
    final currentId = id.trim();
    final otherId = other.id.trim();
    if (currentId.isNotEmpty && otherId.isNotEmpty) {
      return currentId == otherId;
    }
    return _normalizePlaceIdentity(name) ==
            _normalizePlaceIdentity(other.name) &&
        _normalizePlaceIdentity(address) ==
            _normalizePlaceIdentity(other.address);
  }
}

String _normalizePlaceIdentity(String value) => value.trim().toLowerCase();

class MemorialSummary {
  const MemorialSummary({
    required this.days,
    required this.places,
    required this.distance,
  });

  final int days;
  final int places;
  final String distance;

  factory MemorialSummary.fromJson(Map<String, Object?> json) {
    final distanceKm = json['distance_km'];
    return MemorialSummary(
      days: json['days'] as int? ?? 0,
      places: json['places'] as int? ?? 0,
      distance: json['distance'] as String? ??
          (distanceKm == null ? '' : '${distanceKm}km'),
    );
  }

  Map<String, Object?> toJson() {
    return {
      'days': days,
      'places': places,
      'distance': distance,
    };
  }
}

class MemorialDay {
  const MemorialDay({
    required this.date,
    required this.places,
    required this.photos,
    this.photoAssetPaths = const [],
  });

  final String date;
  final List<String> places;
  final int photos;
  final List<String> photoAssetPaths;

  factory MemorialDay.fromJson(Map<String, Object?> json) {
    final rawPlaces = json['places'];
    final rawPhotos = json['photos'];
    return MemorialDay(
      date: json['date'] as String? ?? '',
      places: rawPlaces is List ? rawPlaces.whereType<String>().toList() : [],
      photos:
          rawPhotos is List ? rawPhotos.length : json['photos'] as int? ?? 0,
      photoAssetPaths: const [],
    );
  }

  Map<String, Object?> toJson() {
    return {
      'date': date,
      'places': places,
      'photos': photos,
      'photo_asset_paths': photoAssetPaths,
    };
  }
}
