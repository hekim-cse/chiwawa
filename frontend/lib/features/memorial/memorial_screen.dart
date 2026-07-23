import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/confirmed_route.dart';
import '../../core/models/memorial_map_models.dart';
import '../../core/models/memorial_models.dart';
import '../../core/models/travel_models.dart';
import '../../core/providers/data_providers.dart';
import '../../shared/widgets/async_value_view.dart';
import '../../shared/widgets/app_page_header.dart';
import '../../shared/widgets/app_viewport.dart';
import 'memorial_photo_edits_controller.dart';
import 'widgets/confirmed_route_preview.dart';
import 'widgets/memorial_date_strip.dart';
import 'widgets/memorial_day_photo_section.dart';
import 'widgets/memorial_month_selector.dart';
import 'widgets/memorial_location_sheet.dart';
import 'widgets/memorial_share_sheet.dart';
import 'widgets/paw_map_view.dart';
import 'widgets/trip_summary_card.dart';

class MemorialScreen extends ConsumerWidget {
  const MemorialScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final confirmedRoute = ref.watch(confirmedRouteProvider);
    final selectedMonth = ref.watch(selectedMemorialMonthProvider);
    final selectedDate = ref.watch(selectedMemorialDateProvider);
    final calendar = ref.watch(memorialCalendarProvider(selectedMonth));
    final dayTimeline = ref.watch(editedMemorialDayProvider(selectedDate));
    final pawClusters = ref.watch(editedPawMapProvider(selectedDate));

    return AsyncValueView<MemorialOverview?>(
      value: ref.watch(memorialDataProvider),
      onRetry: () => ref.invalidate(memorialDataProvider),
      builder: (overview) => _body(
        context,
        ref,
        overview,
        confirmedRoute,
        selectedMonth,
        calendar,
        selectedDate,
        dayTimeline,
        pawClusters,
      ),
    );
  }

  Widget _body(
    BuildContext context,
    WidgetRef ref,
    MemorialOverview? overview,
    List<RoutePlace> confirmedRoute,
    MemorialMonth selectedMonth,
    AsyncValue<MemorialCalendar> calendar,
    DateTime selectedDate,
    AsyncValue<MemorialDayTimeline> dayTimeline,
    AsyncValue<List<PawCluster>> pawClusters,
  ) {
    return SafeArea(
      child: ListView(
        key: const ValueKey('memorial-scroll'),
        padding: AppLayout.pageInsets(context),
        children: [
          const AppPageHeader(
            title: '여행 마무리',
            subtitle: '사진과 이동 동선을 날짜별 여행 기록으로 모았어요.',
          ),
          const SizedBox(height: 18),
          if (overview != null) ...[
            TripSummaryCard(
              tripInfo: overview.tripInfo,
              summary: overview.summary,
            ),
            const SizedBox(height: 20),
          ],
          MemorialMonthSelector(
            month: selectedMonth,
            onPrevious: () => _changeMonth(ref, selectedMonth.previous),
            onNext: () => _changeMonth(ref, selectedMonth.next),
          ),
          const SizedBox(height: 6),
          AsyncValueView<MemorialCalendar>(
            value: calendar,
            loadingHeight: 44,
            onRetry: () =>
                ref.invalidate(memorialCalendarProvider(selectedMonth)),
            builder: (data) {
              _selectFirstAvailableDate(ref, data, selectedDate);
              return MemorialDateStrip(
                days: data.days,
                selectedDate: selectedDate,
                onSelected: (date) {
                  ref.read(selectedMemorialDateProvider.notifier).state = date;
                },
              );
            },
          ),
          const SizedBox(height: 12),
          AsyncValueView<MemorialDayTimeline>(
            key: const ValueKey('memorial-day-content'),
            value: dayTimeline,
            loadingHeight: 430,
            onRetry: () => ref.invalidate(memorialDayProvider(selectedDate)),
            builder: (timeline) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AsyncValueView<List<PawCluster>>(
                  value: pawClusters,
                  loadingHeight: 260,
                  onRetry: () =>
                      ref.invalidate(memorialDayProvider(selectedDate)),
                  builder: (clusters) => PawMapView(clusters: clusters),
                ),
                const SizedBox(height: ChiwawaSpacing.section),
                MemorialDayPhotoSection(
                  timeline: timeline,
                  onEditLocation: (photo) =>
                      _editPhotoLocation(context, ref, photo),
                  onExclude: (photo) => _excludePhoto(context, ref, photo),
                ),
              ],
            ),
          ),
          if (confirmedRoute.isNotEmpty) ...[
            const SizedBox(height: 20),
            ConfirmedRoutePreview(places: confirmedRoute),
          ],
          const SizedBox(height: ChiwawaSpacing.lg),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => showMemorialShareSheet(
                context,
                overview: overview,
                date: selectedDate,
                timeline: dayTimeline.valueOrNull,
              ),
              icon: const Icon(Icons.share_rounded, size: 18),
              label: const Text('여행 기록 공유'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _editPhotoLocation(
    BuildContext context,
    WidgetRef ref,
    MemorialPhoto photo,
  ) async {
    final location = await showMemorialLocationSheet(context, photo: photo);
    if (location == null || !context.mounted) return;
    ref.read(memorialPhotoEditsProvider.notifier).updateLocation(
          photo.id,
          address: location.address,
          latitude: location.latitude,
          longitude: location.longitude,
        );
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(content: Text('사진 위치를 수정했어요.')));
  }

  void _excludePhoto(
    BuildContext context,
    WidgetRef ref,
    MemorialPhoto photo,
  ) {
    ref.read(memorialPhotoEditsProvider.notifier).exclude(photo.id);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: const Text('사진을 이 여행 기록에서 제외했어요.'),
          action: SnackBarAction(
            label: '되돌리기',
            onPressed: () =>
                ref.read(memorialPhotoEditsProvider.notifier).restore(photo.id),
          ),
        ),
      );
  }

  void _changeMonth(WidgetRef ref, MemorialMonth month) {
    ref.read(selectedMemorialMonthProvider.notifier).state = month;
    ref.read(selectedMemorialDateProvider.notifier).state = month.firstDay;
  }

  void _selectFirstAvailableDate(
    WidgetRef ref,
    MemorialCalendar calendar,
    DateTime selectedDate,
  ) {
    if (calendar.days.isEmpty ||
        calendar.days.any(
          (day) => isSameMemorialDay(day.day, selectedDate),
        )) {
      return;
    }

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final selectedMonth = ref.read(selectedMemorialMonthProvider);
      if (selectedMonth.year != calendar.year ||
          selectedMonth.month != calendar.month) {
        return;
      }
      ref.read(selectedMemorialDateProvider.notifier).state =
          calendar.days.first.day;
    });
  }
}
