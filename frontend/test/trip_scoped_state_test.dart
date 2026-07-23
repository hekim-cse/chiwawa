import 'package:chiwawa/core/confirmed_route.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/saved_photo_places.dart';
import 'package:chiwawa/core/services/trip_session_service.dart';
import 'package:chiwawa/features/memorial/memorial_photo_edits_controller.dart';
import 'package:chiwawa/features/plan/plan_controller.dart';
import 'package:chiwawa/features/plan/models/plan_place_selection.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const place = PhotoSearchResult(
    id: 'place-1',
    name: '여행별 장소',
    address: '도쿄',
    category: '명소',
  );
  const route = RoutePlace(
    name: '여행별 일정',
    duration: '60분',
    transport: '도보 5분',
    category: '명소',
  );

  test('saved photo places are preserved separately for each trip', () {
    final store = SavedPhotoPlaceStore();
    final firstTrip = SavedPhotoPlacesNotifier(
      store: store,
      tripId: 'trip-a',
    );
    final secondTrip = SavedPhotoPlacesNotifier(
      store: store,
      tripId: 'trip-b',
    );
    addTearDown(firstTrip.dispose);
    addTearDown(secondTrip.dispose);

    firstTrip.addPlace(place);

    expect(firstTrip.state, [place]);
    expect(secondTrip.state, isEmpty);

    final restoredFirstTrip = SavedPhotoPlacesNotifier(
      store: store,
      tripId: 'trip-a',
    );
    addTearDown(restoredFirstTrip.dispose);
    expect(restoredFirstTrip.state, [place]);
  });

  test('trip switch clears draft route and memorial edit state', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    container.read(planItineraryProvider.notifier).replaceCurrentDay(
      const [route],
    );
    container.read(selectedPlacesProvider.notifier).state = const [
      PlanPlaceSelection(
        id: 'manual:previous-trip',
        name: '이전 여행 장소',
        source: PlanPlaceSource.manual,
      ),
    ];
    container.read(confirmedRouteProvider.notifier).confirm(const [route]);
    container.read(memorialPhotoEditsProvider.notifier).exclude('photo-1');

    container.read(currentTripRevisionProvider.notifier).state += 1;

    expect(container.read(planItineraryProvider).currentStops, isEmpty);
    expect(
      container.read(selectedPlacesProvider).map((place) => place.name),
      isNot(contains('이전 여행 장소')),
    );
    expect(container.read(confirmedRouteProvider), isEmpty);
    expect(container.read(memorialPhotoEditsProvider), isEmpty);
  });
}
