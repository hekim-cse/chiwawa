import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../../../shared/widgets/app_viewport.dart';
import '../../../shared/widgets/app_section_header.dart';
import '../../../shared/widgets/app_status_view.dart';
import '../trip_controller.dart';
import 'trip_inline_error.dart';
import 'trip_list_item.dart';

class TripListContent extends StatelessWidget {
  const TripListContent({
    required this.catalog,
    required this.onRetry,
    required this.onAdd,
    required this.onSelect,
    super.key,
  });

  final TripCatalogState catalog;
  final Future<void> Function() onRetry;
  final VoidCallback onAdd;
  final ValueChanged<Trip> onSelect;

  @override
  Widget build(BuildContext context) {
    if (catalog.status == TripCatalogStatus.initial ||
        catalog.status == TripCatalogStatus.loading) {
      return const _TripListLoading();
    }

    if (catalog.status == TripCatalogStatus.error && catalog.trips.isEmpty) {
      return _TripErrorState(
        message: catalog.errorMessage ?? '여행 목록을 불러오지 못했어요.',
        onRetry: onRetry,
      );
    }

    if (catalog.trips.isEmpty) return _TripEmptyState(onAdd: onAdd);

    final currentTrip = catalog.currentTrip;
    final otherTrips = catalog.trips
        .where((trip) => trip.id != catalog.currentTripId)
        .toList(growable: false);

    return RefreshIndicator(
      onRefresh: onRetry,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: AppLayout.pageInsets(context, top: 12, bottom: 28),
        children: [
          const Text(
            '여행을 바꾸면 홈, 일정, 기록이 선택한 여행 기준으로 이어져요.',
            style: TextStyle(
              color: ChiwawaColors.textSecondary,
              fontSize: 13,
              height: 1.45,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (catalog.errorMessage != null) ...[
            const SizedBox(height: ChiwawaSpacing.sm),
            TripInlineError(message: catalog.errorMessage!),
          ],
          if (currentTrip != null) ...[
            const SizedBox(height: ChiwawaSpacing.section),
            const AppSectionHeader(title: '현재 여행'),
            const SizedBox(height: ChiwawaSpacing.sm),
            TripListItem(
              key: ValueKey('trip-list-item-${currentTrip.id}'),
              trip: currentTrip,
              isCurrent: true,
              onTap: null,
            ),
          ],
          if (otherTrips.isNotEmpty) ...[
            const SizedBox(height: ChiwawaSpacing.section),
            AppSectionHeader(
              title: '다른 여행',
              trailing: Text(
                '${otherTrips.length}개',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: ChiwawaColors.textSecondary,
                    ),
              ),
            ),
            const SizedBox(height: ChiwawaSpacing.sm),
            for (var index = 0; index < otherTrips.length; index++) ...[
              TripListItem(
                key: ValueKey('trip-list-item-${otherTrips[index].id}'),
                trip: otherTrips[index],
                isCurrent: false,
                onTap: () => onSelect(otherTrips[index]),
              ),
              if (index != otherTrips.length - 1)
                const SizedBox(height: ChiwawaSpacing.xs),
            ],
          ],
        ],
      ),
    );
  }
}

class _TripListLoading extends StatelessWidget {
  const _TripListLoading();

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: AppLayout.pageInsets(context, top: 12, bottom: 28),
      itemCount: 3,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) => Container(
        height: 116,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(ChiwawaRadii.control),
          border: Border.all(color: ChiwawaColors.border),
        ),
      ),
    );
  }
}

class _TripEmptyState extends StatelessWidget {
  const _TripEmptyState({required this.onAdd});

  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: AppStatusView(
        kind: AppStatusKind.empty,
        title: '아직 만든 여행이 없어요',
        message: '첫 여행을 만들면 장소와 일정을 여행별로 이어갈 수 있어요.',
        actionLabel: '여행 만들기',
        onAction: onAdd,
      ),
    );
  }
}

class _TripErrorState extends StatelessWidget {
  const _TripErrorState({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: AppStatusView(
        kind: AppStatusKind.error,
        title: '여행 목록을 불러오지 못했어요',
        message: message,
        actionLabel: '다시 시도',
        onAction: onRetry,
      ),
    );
  }
}
