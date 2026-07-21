import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../env.dart';
import '../auth/auth_controller.dart';
import '../models/memorial_map_models.dart';
import '../models/memorial_models.dart';
import '../models/travel_models.dart';
import '../repositories/memorial_repository.dart';
import '../repositories/photo_place_repository.dart';
import '../repositories/trip_repository.dart';
import '../services/trip_session_service.dart';
import '../utils/geo_cluster.dart';

/// 화면이 소비하는 비동기 데이터 Provider 모음.
/// 화면은 Repository를 직접 부르지 않고 이 Provider들의 AsyncValue만 바라본다.

typedef HomeData = ({TripInfo tripInfo, List<ScheduleItem> schedules});
final tripInfoProvider = FutureProvider<TripInfo>(
  (ref) {
    ref.watch(currentTripRevisionProvider);
    return ref.watch(tripRepositoryProvider).fetchCurrentTrip();
  },
);

final todaySchedulesProvider = FutureProvider<List<ScheduleItem>>(
  (ref) {
    ref.watch(currentTripRevisionProvider);
    return ref.watch(tripRepositoryProvider).fetchTodaySchedules();
  },
);

final freeTimeRecommendsProvider = FutureProvider<List<FreeTimeRecommend>>(
  (ref) {
    ref.watch(currentTripRevisionProvider);
    return ref.watch(tripRepositoryProvider).fetchFreeTimeRecommendations();
  },
);

final homeDataProvider = FutureProvider<HomeData>((ref) async {
  ref.watch(currentTripRevisionProvider);
  final repository = ref.watch(tripRepositoryProvider);
  final tripInfo = await repository.fetchCurrentTrip();
  final schedules = await repository.fetchTodaySchedules();
  return (tripInfo: tripInfo, schedules: schedules);
});

final memorialDataProvider = FutureProvider<MemorialOverview?>((ref) {
  ref.watch(currentTripRevisionProvider);
  return ref.watch(memorialRepositoryProvider).fetchOverview();
});

DateTime _initialMemorialDate() {
  if (useApiBackend) {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day);
  }
  return DateTime(2025, 4, 1);
}

final selectedMemorialMonthProvider = StateProvider<MemorialMonth>(
  (ref) {
    ref.watch(authSessionRevisionProvider);
    ref.watch(currentTripRevisionProvider);
    return MemorialMonth.fromDate(_initialMemorialDate());
  },
);

final selectedMemorialDateProvider = StateProvider<DateTime>(
  (ref) {
    ref.watch(authSessionRevisionProvider);
    ref.watch(currentTripRevisionProvider);
    return _initialMemorialDate();
  },
);

final memorialCalendarProvider =
    FutureProvider.family<MemorialCalendar, MemorialMonth>(
  (ref, month) {
    ref.watch(currentTripRevisionProvider);
    return ref.watch(memorialRepositoryProvider).fetchCalendar(month);
  },
);

final memorialDayProvider =
    FutureProvider.family<MemorialDayTimeline, DateTime>(
  (ref, date) {
    ref.watch(currentTripRevisionProvider);
    return ref.watch(memorialRepositoryProvider).fetchDay(date);
  },
);

final pawMapProvider = FutureProvider.family<List<PawCluster>, DateTime>(
  (ref, date) async {
    final timeline = await ref.watch(memorialDayProvider(date).future);
    final points = <MemorialPhotoPoint>[
      for (final entry in timeline.items)
        if (entry.photo.hasCoordinates)
          MemorialPhotoPoint(
            id: entry.photo.id,
            takenAt: entry.photo.takenAt,
            latitude: entry.photo.latitude!,
            longitude: entry.photo.longitude!,
            placeName: _photoPlaceName(entry.photo),
            assetPath: entry.photo.assetPath,
            fileUrl: entry.photo.fileUrl,
          ),
    ];
    return clusterPawPrints(points);
  },
);

final memorialPhotoBytesProvider =
    FutureProvider.family<Uint8List, String>((ref, fileUrl) {
  return ref.watch(memorialRepositoryProvider).fetchPhotoBytes(fileUrl);
});

final recentPhotoSearchesProvider = FutureProvider<List<PhotoSearchResult>>(
  (ref) => ref.watch(photoPlaceRepositoryProvider).fetchRecentSearches(),
);

String _photoPlaceName(MemorialPhoto photo) {
  final address = photo.address?.trim();
  return address == null || address.isEmpty ? '위치 정보 없음' : address;
}
