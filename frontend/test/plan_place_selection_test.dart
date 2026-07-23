import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/features/plan/plan_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('same-name saved places stay independent by place id', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    container.read(selectedPlacesProvider.notifier).state = const [];
    final actions = container.read(planActionsProvider);

    const tokyo = PhotoSearchResult(
      id: 'central-park-tokyo',
      name: '중앙 공원',
      address: '도쿄 치요다구',
      category: '공원',
    );
    const osaka = PhotoSearchResult(
      id: 'central-park-osaka',
      name: '중앙 공원',
      address: '오사카 주오구',
      category: '공원',
    );

    expect(actions.addSavedPlace(tokyo), isTrue);
    expect(actions.addSavedPlace(osaka), isTrue);
    expect(actions.addSavedPlace(tokyo), isFalse);

    final selections = container.read(selectedPlacesProvider);
    expect(selections, hasLength(2));
    expect(selections.map((place) => place.name), everyElement('중앙 공원'));
    expect(selections.map((place) => place.id).toSet(), hasLength(2));

    actions.removePlace(selections.first);

    final remaining = container.read(selectedPlacesProvider);
    expect(remaining, hasLength(1));
    expect(remaining.single.id, isNot(selections.first.id));
  });

  test('same-name manual places can be removed one at a time', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    container.read(selectedPlacesProvider.notifier).state = const [];
    final actions = container.read(planActionsProvider);

    expect(actions.addPlace('시청'), isTrue);
    expect(actions.addPlace('시청'), isTrue);

    final selections = container.read(selectedPlacesProvider);
    expect(selections, hasLength(2));
    expect(selections.map((place) => place.id).toSet(), hasLength(2));

    actions.removePlace(selections.last);

    final remaining = container.read(selectedPlacesProvider);
    expect(remaining, hasLength(1));
    expect(remaining.single.id, selections.first.id);
    expect(remaining.single.name, '시청');
  });
}
