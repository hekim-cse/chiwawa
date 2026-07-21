import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth/auth_controller.dart';
import 'models/travel_models.dart';
import 'services/trip_session_service.dart';

final confirmedRouteProvider =
    StateNotifierProvider<ConfirmedRouteNotifier, List<RoutePlace>>(
  (ref) {
    ref.watch(authSessionRevisionProvider);
    ref.watch(currentTripRevisionProvider);
    return ConfirmedRouteNotifier();
  },
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
