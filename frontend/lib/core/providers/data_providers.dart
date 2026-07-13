import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/memorial_map_models.dart';
import '../models/travel_models.dart';
import '../repositories/photo_place_repository.dart';
import '../repositories/trip_repository.dart';
import '../utils/geo_cluster.dart';

/// 화면이 소비하는 비동기 데이터 Provider 모음.
/// 화면은 Repository를 직접 부르지 않고 이 Provider들의 AsyncValue만 바라본다.

typedef HomeData = ({TripInfo tripInfo, List<ScheduleItem> schedules});
typedef MemorialData = ({
  TripInfo tripInfo,
  MemorialSummary summary,
  List<MemorialDay> days,
});

final tripInfoProvider = FutureProvider<TripInfo>(
  (ref) => ref.watch(tripRepositoryProvider).fetchCurrentTrip(),
);

final todaySchedulesProvider = FutureProvider<List<ScheduleItem>>(
  (ref) => ref.watch(tripRepositoryProvider).fetchTodaySchedules(),
);

final freeTimeRecommendsProvider = FutureProvider<List<FreeTimeRecommend>>(
  (ref) => ref.watch(tripRepositoryProvider).fetchFreeTimeRecommendations(),
);

final homeDataProvider = FutureProvider<HomeData>((ref) async {
  final repository = ref.watch(tripRepositoryProvider);
  final tripInfo = await repository.fetchCurrentTrip();
  final schedules = await repository.fetchTodaySchedules();
  return (tripInfo: tripInfo, schedules: schedules);
});

final memorialDataProvider = FutureProvider<MemorialData>((ref) async {
  final repository = ref.watch(tripRepositoryProvider);
  final tripInfo = await repository.fetchCurrentTrip();
  final summary = await repository.fetchMemorialSummary();
  final days = await repository.fetchMemorialDays();
  return (tripInfo: tripInfo, summary: summary, days: days);
});

final memorialDateOptionsProvider = FutureProvider<List<DateTime>>(
  (ref) => ref.watch(tripRepositoryProvider).fetchMemorialDates(),
);

final selectedMemorialDateProvider = StateProvider<DateTime>(
  (ref) => DateTime(2025, 4, 1),
);

final pawMapProvider = FutureProvider.family<List<PawCluster>, DateTime>(
  (ref, date) async {
    final points =
        await ref.watch(tripRepositoryProvider).fetchMemorialPhotoPoints(date);
    return clusterPawPrints(points);
  },
);

final recentPhotoSearchesProvider = FutureProvider<List<PhotoSearchResult>>(
  (ref) => ref.watch(photoPlaceRepositoryProvider).fetchRecentSearches(),
);
