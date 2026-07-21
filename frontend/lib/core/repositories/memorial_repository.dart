import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/dio_client.dart';
import '../auth/auth_controller.dart';
import '../env.dart';
import '../mock_data.dart' as mock;
import '../models/memorial_models.dart';
import 'api/api_memorial_repository.dart';

final memorialRepositoryProvider = Provider<MemorialRepository>((ref) {
  ref.watch(authSessionRevisionProvider);
  if (useApiBackend) {
    return ApiMemorialRepository(dio: ref.watch(dioClientProvider));
  }
  return const MockMemorialRepository();
});

abstract class MemorialRepository {
  Future<MemorialOverview?> fetchOverview();
  Future<MemorialCalendar> fetchCalendar(MemorialMonth month);
  Future<MemorialDayTimeline> fetchDay(DateTime day);
  Future<Uint8List> fetchPhotoBytes(String fileUrl);
}

class MockMemorialRepository implements MemorialRepository {
  const MockMemorialRepository();

  @override
  Future<MemorialOverview?> fetchOverview() async {
    return const MemorialOverview(
      tripInfo: mock.tripInfo,
      summary: mock.memorialSummary,
      days: mock.memorialDays,
    );
  }

  @override
  Future<MemorialCalendar> fetchCalendar(MemorialMonth month) async {
    final days = mock.memorialTripDates
        .where((date) => date.year == month.year && date.month == month.month)
        .map(
          (date) => MemorialCalendarDay(
            day: date,
            photoCount: mock.memorialPhotoPoints
                .where((point) => isSameMemorialDay(point.takenAt, date))
                .length,
          ),
        )
        .toList();
    return MemorialCalendar(
      year: month.year,
      month: month.month,
      days: List.unmodifiable(days),
    );
  }

  @override
  Future<MemorialDayTimeline> fetchDay(DateTime day) async {
    final points = mock.memorialPhotoPoints
        .where((point) => isSameMemorialDay(point.takenAt, day))
        .toList()
      ..sort((a, b) => a.takenAt.compareTo(b.takenAt));

    return MemorialDayTimeline(
      day: day,
      items: List.unmodifiable([
        for (var index = 0; index < points.length; index++)
          MemorialTimelineEntry(
            seq: index,
            photo: MemorialPhoto(
              id: points[index].id,
              fileName: points[index].assetPath.split('/').last,
              contentType: 'image/png',
              takenAt: points[index].takenAt,
              latitude: points[index].latitude,
              longitude: points[index].longitude,
              address: points[index].placeName,
              fileUrl: '',
              createdAt: points[index].takenAt,
              assetPath: points[index].assetPath,
            ),
          ),
      ]),
    );
  }

  @override
  Future<Uint8List> fetchPhotoBytes(String fileUrl) {
    throw UnsupportedError('Mock memorial photos use bundled assets.');
  }
}
