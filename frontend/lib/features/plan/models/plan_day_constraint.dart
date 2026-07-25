import '../../../core/models/place_search_models.dart';

class PlanDayConstraint {
  const PlanDayConstraint({
    this.startPlace,
    this.startTime = '09:00',
    this.endPlace,
    this.endTime = '20:00',
    this.maxPlaceCount = 4,
  });

  static const minimumPlaceCount = 1;
  static const maximumPlaceCount = 8;

  final PlaceSearchCandidate? startPlace;
  final String startTime;
  final PlaceSearchCandidate? endPlace;
  final String endTime;
  final int maxPlaceCount;

  bool get isValid => validationMessage == null;

  String? get validationMessage {
    if (startPlace == null || endPlace == null) {
      return '검색 결과에서 출발지와 도착지를 선택해 주세요.';
    }
    if (!startPlace!.isValid || !endPlace!.isValid) {
      return '선택한 장소 정보를 다시 확인해 주세요.';
    }

    final startMinutes = _minutesFromTime(startTime);
    final endMinutes = _minutesFromTime(endTime);
    if (startMinutes == null || endMinutes == null) {
      return '출발과 도착 시간을 다시 선택해 주세요.';
    }
    if (endMinutes <= startMinutes) {
      return '도착 시간은 출발 시간보다 늦어야 해요.';
    }
    return null;
  }

  PlanDayConstraint copyWith({
    PlaceSearchCandidate? startPlace,
    bool clearStartPlace = false,
    String? startTime,
    PlaceSearchCandidate? endPlace,
    bool clearEndPlace = false,
    String? endTime,
    int? maxPlaceCount,
  }) {
    return PlanDayConstraint(
      startPlace: clearStartPlace ? null : startPlace ?? this.startPlace,
      startTime: startTime ?? this.startTime,
      endPlace: clearEndPlace ? null : endPlace ?? this.endPlace,
      endTime: endTime ?? this.endTime,
      maxPlaceCount: (maxPlaceCount ?? this.maxPlaceCount)
          .clamp(
            minimumPlaceCount,
            maximumPlaceCount,
          )
          .toInt(),
    );
  }
}

class PlanDayConstraintsState {
  const PlanDayConstraintsState({this.constraintsByDay = const {}});

  final Map<int, PlanDayConstraint> constraintsByDay;

  PlanDayConstraint forDay(int day) {
    return constraintsByDay[day] ?? const PlanDayConstraint();
  }

  PlanDayConstraintsState copyWith({
    Map<int, PlanDayConstraint>? constraintsByDay,
  }) {
    return PlanDayConstraintsState(
      constraintsByDay: constraintsByDay ?? this.constraintsByDay,
    );
  }
}

int? _minutesFromTime(String value) {
  final parts = value.split(':');
  if (parts.length != 2) return null;

  final hour = int.tryParse(parts[0]);
  final minute = int.tryParse(parts[1]);
  if (hour == null ||
      minute == null ||
      hour < 0 ||
      hour > 23 ||
      minute < 0 ||
      minute > 59) {
    return null;
  }
  return hour * 60 + minute;
}
