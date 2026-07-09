import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'models/travel_models.dart';

final confirmedRouteProvider =
    StateNotifierProvider<ConfirmedRouteNotifier, List<RoutePlace>>(
  (ref) => ConfirmedRouteNotifier(),
);

class ConfirmedRouteNotifier extends StateNotifier<List<RoutePlace>> {
  ConfirmedRouteNotifier() : super(const []);

  void confirm(List<RoutePlace> places) {
    state = List.unmodifiable(places);
  }

  void clear() {
    state = const [];
  }
}
