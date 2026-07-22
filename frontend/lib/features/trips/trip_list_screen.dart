import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/models/travel_models.dart';
import 'trip_controller.dart';
import 'widgets/trip_app_bar.dart';
import 'widgets/trip_create_sheet.dart';
import 'widgets/trip_list_content.dart';

class TripListScreen extends ConsumerWidget {
  const TripListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final catalog = ref.watch(tripCatalogProvider);

    return SafeArea(
      child: ColoredBox(
        color: ChiwawaColors.background,
        child: Column(
          children: [
            TripAppBar(
              onBack: () => context.go('/mypage'),
              onAdd: () => _createTrip(context),
            ),
            Expanded(
              child: TripListContent(
                catalog: catalog,
                onRetry: ref.read(tripCatalogProvider.notifier).load,
                onAdd: () => _createTrip(context),
                onSelect: (trip) => _selectTrip(context, ref, trip),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _selectTrip(
    BuildContext context,
    WidgetRef ref,
    Trip trip,
  ) async {
    await ref.read(tripCatalogProvider.notifier).selectTrip(trip.id);
    if (!context.mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text('${trip.title}(으)로 전환했어요.')));
  }

  Future<void> _createTrip(BuildContext context) async {
    final created = await showTripCreateSheet(context);
    if (created == null || !context.mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(content: Text('${created.title}을(를) 만들고 현재 여행으로 설정했어요.')),
      );
  }
}
