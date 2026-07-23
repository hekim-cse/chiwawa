class PlanDayConstraint {
  const PlanDayConstraint({
    this.startPlace = '숙소',
    this.startTime = '09:00',
    this.endPlace = '숙소',
    this.endTime = '20:00',
    this.maxPlaceCount = 4,
  });

  static const minimumPlaceCount = 1;
  static const maximumPlaceCount = 8;

  final String startPlace;
  final String startTime;
  final String endPlace;
  final String endTime;
  final int maxPlaceCount;

  bool get isValid => validationMessage == null;

  String? get validationMessage {
    if (startPlace.trim().isEmpty || endPlace.trim().isEmpty) {
      return '출발지와 도착지를 모두 입력해 주세요.';
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
    String? startPlace,
    String? startTime,
    String? endPlace,
    String? endTime,
    int? maxPlaceCount,
  }) {
    return PlanDayConstraint(
      startPlace: startPlace ?? this.startPlace,
      startTime: startTime ?? this.startTime,
      endPlace: endPlace ?? this.endPlace,
      endTime: endTime ?? this.endTime,
      maxPlaceCount: (maxPlaceCount ?? this.maxPlaceCount)
          .clamp(minimumPlaceCount, maximumPlaceCount)
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
