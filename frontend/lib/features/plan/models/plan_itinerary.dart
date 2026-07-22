import '../../../core/models/travel_models.dart';

class PlanItineraryStop {
  const PlanItineraryStop({
    required this.id,
    required this.startTime,
    required this.place,
  });

  final String id;
  final String startTime;
  final RoutePlace place;

  PlanItineraryStop copyWith({String? startTime}) {
    return PlanItineraryStop(
      id: id,
      startTime: startTime ?? this.startTime,
      place: place,
    );
  }
}

class PlanItineraryState {
  const PlanItineraryState({
    this.selectedDay = 1,
    this.stopsByDay = const {},
  });

  final int selectedDay;
  final Map<int, List<PlanItineraryStop>> stopsByDay;

  List<PlanItineraryStop> get currentStops =>
      stopsByDay[selectedDay] ?? const [];

  PlanItineraryState copyWith({
    int? selectedDay,
    Map<int, List<PlanItineraryStop>>? stopsByDay,
  }) {
    return PlanItineraryState(
      selectedDay: selectedDay ?? this.selectedDay,
      stopsByDay: stopsByDay ?? this.stopsByDay,
    );
  }
}
