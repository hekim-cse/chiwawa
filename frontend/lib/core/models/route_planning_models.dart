import '../utils/time_formatters.dart';
import 'place_search_models.dart';
import 'transport_mode.dart';
import 'travel_models.dart';

enum RouteOptionAvailability { success, unavailable }

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

  PlanRoutePlaceInput copyWith({String? serverPlaceId}) {
    return PlanRoutePlaceInput(
      localId: localId,
      serverPlaceId: serverPlaceId ?? this.serverPlaceId,
      name: name,
      address: address,
      latitude: latitude,
      longitude: longitude,
    );
  }
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
    required this.startPlace,
    required this.endPlace,
  });

  final List<PlanRoutePlaceInput> places;
  final TravelPreference preference;
  final TransportMode transportMode;
  final int dayIndex;
  final String plannedStartTime;
  final String plannedEndTime;
  final int maxPlaceCount;
  final PlaceSearchCandidate startPlace;
  final PlaceSearchCandidate endPlace;

  List<String> get wantedPlaceIds => [
        for (final place in places)
          if (place.isPersisted) place.serverPlaceId!,
      ];
}

class RouteTimelineStop {
  const RouteTimelineStop({
    required this.stopType,
    required this.placeId,
    required this.name,
    required this.arrivalAt,
    required this.departureAt,
    required this.stayMinutes,
  });

  final String stopType;
  final String placeId;
  final String name;
  final String arrivalAt;
  final String departureAt;
  final int stayMinutes;

  String get arrivalTime => _dateTimeToTime(arrivalAt);
  String get departureTime => _dateTimeToTime(departureAt);

  factory RouteTimelineStop.fromJson(Map<String, Object?> json) {
    return RouteTimelineStop(
      stopType: json['stop_type'] as String? ?? 'POI',
      placeId: json['place_id']?.toString() ?? '',
      name: json['name'] as String? ?? '',
      arrivalAt: json['arrival_at'] as String? ?? '',
      departureAt: json['departure_at'] as String? ?? '',
      stayMinutes: (json['stay_minutes'] as num?)?.toInt() ?? 0,
    );
  }
}

class RouteTimeline {
  const RouteTimeline({
    required this.dayIndex,
    required this.travelMode,
    required this.plannedStartAt,
    required this.plannedEndAt,
    required this.actualEndAt,
    required this.totalTravelMinutes,
    required this.totalStayMinutes,
    required this.timelineStops,
    this.exceedsPlannedEnd = false,
    this.warnings = const [],
  });

  final int dayIndex;
  final TransportMode travelMode;
  final String plannedStartAt;
  final String plannedEndAt;
  final String actualEndAt;
  final int totalTravelMinutes;
  final int totalStayMinutes;
  final List<RouteTimelineStop> timelineStops;
  final bool exceedsPlannedEnd;
  final List<String> warnings;

  String get actualEndTime => _dateTimeToTime(actualEndAt);
  String get plannedEndTime => _dateTimeToTime(plannedEndAt);

  factory RouteTimeline.fromJson(Map<String, Object?> json) {
    final rawStops = json['timeline_stops'] as List<Object?>? ?? const [];
    final rawWarnings = json['warnings'] as List<Object?>? ?? const [];
    return RouteTimeline(
      dayIndex: (json['day_index'] as num?)?.toInt() ?? 1,
      travelMode: TransportModeMapping.fromAiCode(
        json['travel_mode'] as String?,
      ),
      plannedStartAt: json['planned_start_at'] as String? ?? '',
      plannedEndAt: json['planned_end_at'] as String? ?? '',
      actualEndAt: json['actual_end_at'] as String? ?? '',
      totalTravelMinutes: (json['total_travel_minutes'] as num?)?.toInt() ?? 0,
      totalStayMinutes: (json['total_stay_minutes'] as num?)?.toInt() ?? 0,
      timelineStops: [
        for (final raw in rawStops)
          RouteTimelineStop.fromJson(
            Map<String, Object?>.from(raw! as Map),
          ),
      ],
      exceedsPlannedEnd: json['exceeds_planned_end'] as bool? ?? false,
      warnings: rawWarnings.whereType<String>().toList(growable: false),
    );
  }
}

class RouteRecommendationCandidate {
  const RouteRecommendationCandidate({
    required this.placeId,
    required this.name,
    required this.formattedAddress,
    required this.latitude,
    required this.longitude,
    this.rating,
    this.userRatingCount,
  });

  final String placeId;
  final String name;
  final String formattedAddress;
  final double latitude;
  final double longitude;
  final double? rating;
  final int? userRatingCount;

  factory RouteRecommendationCandidate.fromJson(Map<String, Object?> json) {
    final coordinate = json['coordinate'] as Map<Object?, Object?>? ?? const {};
    return RouteRecommendationCandidate(
      placeId: json['place_id']?.toString() ?? '',
      name: json['name'] as String? ?? '',
      formattedAddress: json['formatted_address'] as String? ?? '',
      latitude: (coordinate['lat'] as num?)?.toDouble() ??
          (json['latitude'] as num?)?.toDouble() ??
          0,
      longitude: (coordinate['lng'] as num?)?.toDouble() ??
          (json['longitude'] as num?)?.toDouble() ??
          0,
      rating: (json['rating'] as num?)?.toDouble(),
      userRatingCount: (json['user_rating_count'] as num?)?.toInt() ??
          (json['review_count'] as num?)?.toInt(),
    );
  }
}

class RouteInsertionImpact {
  const RouteInsertionImpact({
    required this.previousPlaceId,
    required this.nextPlaceId,
    required this.additionalMinutes,
    required this.candidateArrivalAt,
    required this.candidateDepartureAt,
    required this.updatedNextArrivalAt,
    required this.updatedTimelineEndAt,
  });

  final String previousPlaceId;
  final String nextPlaceId;
  final int additionalMinutes;
  final String candidateArrivalAt;
  final String candidateDepartureAt;
  final String updatedNextArrivalAt;
  final String updatedTimelineEndAt;

  String get candidateArrivalTime => _dateTimeToTime(candidateArrivalAt);
  String get candidateDepartureTime => _dateTimeToTime(candidateDepartureAt);
  String get updatedNextArrivalTime => _dateTimeToTime(updatedNextArrivalAt);
  String get updatedTimelineEndTime => _dateTimeToTime(updatedTimelineEndAt);

  int get stayMinutes {
    final arrival = DateTime.tryParse(candidateArrivalAt);
    final departure = DateTime.tryParse(candidateDepartureAt);
    if (arrival == null || departure == null) return 0;
    return departure.difference(arrival).inMinutes.clamp(0, 1440);
  }

  factory RouteInsertionImpact.fromJson(Map<String, Object?> json) {
    return RouteInsertionImpact(
      previousPlaceId: json['previous_place_id']?.toString() ?? '',
      nextPlaceId: json['next_place_id']?.toString() ?? '',
      additionalMinutes: (json['additional_minutes'] as num?)?.toInt() ?? 0,
      candidateArrivalAt: json['candidate_arrival_at'] as String? ?? '',
      candidateDepartureAt: json['candidate_departure_at'] as String? ?? '',
      updatedNextArrivalAt: json['updated_next_arrival_at'] as String? ?? '',
      updatedTimelineEndAt: json['updated_timeline_end_at'] as String? ?? '',
    );
  }
}

class RouteRecommendation {
  const RouteRecommendation({
    required this.candidate,
    required this.insertionImpact,
  });

  final RouteRecommendationCandidate candidate;
  final RouteInsertionImpact insertionImpact;

  factory RouteRecommendation.fromJson(Map<String, Object?> json) {
    return RouteRecommendation(
      candidate: RouteRecommendationCandidate.fromJson(
        Map<String, Object?>.from(
          json['candidate'] as Map? ?? const {},
        ),
      ),
      insertionImpact: RouteInsertionImpact.fromJson(
        Map<String, Object?>.from(
          json['insertion_impact'] as Map? ?? const {},
        ),
      ),
    );
  }
}

class RouteRecommendationGroup {
  const RouteRecommendationGroup({
    required this.category,
    required this.displayName,
    required this.recommendations,
  });

  final String category;
  final String displayName;
  final List<RouteRecommendation> recommendations;

  factory RouteRecommendationGroup.fromJson(Map<String, Object?> json) {
    final rawRecommendations =
        json['recommendations'] as List<Object?>? ?? const [];
    return RouteRecommendationGroup(
      category: json['category']?.toString() ?? '',
      displayName: json['display_name'] as String? ?? '',
      recommendations: [
        for (final raw in rawRecommendations)
          RouteRecommendation.fromJson(
            Map<String, Object?>.from(raw! as Map),
          ),
      ],
    );
  }
}

class RouteOptimizationResult {
  const RouteOptimizationResult({
    required this.availability,
    this.places = const [],
    this.timeline,
    this.missingSegments = const [],
    this.warnings = const [],
    this.recommendationGroups = const [],
  });

  const RouteOptimizationResult.success({
    required List<RoutePlace> places,
    RouteTimeline? timeline,
    List<String> warnings = const [],
    List<RouteRecommendationGroup> recommendationGroups = const [],
  }) : this(
          availability: RouteOptionAvailability.success,
          places: places,
          timeline: timeline,
          warnings: warnings,
          recommendationGroups: recommendationGroups,
        );

  const RouteOptimizationResult.unavailable({
    List<String> missingSegments = const [],
    List<String> warnings = const [],
  }) : this(
          availability: RouteOptionAvailability.unavailable,
          missingSegments: missingSegments,
          warnings: warnings,
        );

  final RouteOptionAvailability availability;
  final List<RoutePlace> places;
  final RouteTimeline? timeline;
  final List<String> missingSegments;
  final List<String> warnings;
  final List<RouteRecommendationGroup> recommendationGroups;

  bool get isAvailable => availability == RouteOptionAvailability.success;
}

class RouteOptimizationState {
  const RouteOptimizationState({
    required this.status,
    this.result,
    this.message,
  });

  const RouteOptimizationState.idle()
      : status = AiJobStatus.idle,
        result = null,
        message = null;

  const RouteOptimizationState.pending()
      : status = AiJobStatus.pending,
        result = null,
        message = null;

  const RouteOptimizationState.running()
      : status = AiJobStatus.running,
        result = null,
        message = null;

  const RouteOptimizationState.done(RouteOptimizationResult routeResult)
      : status = AiJobStatus.done,
        result = routeResult,
        message = null;

  const RouteOptimizationState.failed(String failureMessage)
      : status = AiJobStatus.failed,
        result = null,
        message = failureMessage;

  final AiJobStatus status;
  final RouteOptimizationResult? result;
  final String? message;

  List<RoutePlace> get places => result?.places ?? const [];

  bool get isWorking =>
      status == AiJobStatus.pending || status == AiJobStatus.running;
}

String _dateTimeToTime(String value) {
  final trimmed = value.trim();
  if (trimmed.isEmpty) return '';
  final timePart = trimmed.contains('T') ? trimmed.split('T').last : trimmed;
  return formatTime(timePart);
}
