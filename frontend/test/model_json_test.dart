import 'package:flutter_test/flutter_test.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/auth_repository.dart';

void main() {
  test('ScheduleItem parses and serializes API fields', () {
    final schedule = ScheduleItem.fromJson(const {
      'id': 'schedule-1',
      'trip_id': 'trip-1',
      'name': '아사쿠사 센소지',
      'date': '2025-04-03',
      'start_time': '09:00',
      'end_time': '10:30',
      'place_id': 'place-1',
      'notes': '오전 방문',
      'source': 'manual',
    });

    expect(schedule.id, 'schedule-1');
    expect(schedule.tripId, 'trip-1');
    expect(schedule.startTime, '09:00');
    expect(schedule.place, '아사쿠사 센소지');
    expect(schedule.toJson()['source'], 'manual');
  });

  test('PhotoSearchResult round trips place analysis fields', () {
    final place = PhotoSearchResult.fromJson(const {
      'place_id': 'place-sensoji',
      'name': '아사쿠사 센소지',
      'address': '도쿄 다이토구',
      'category': '사찰·관광지',
      'latitude': 35.7148,
      'longitude': 139.7967,
      'confidence': 0.92,
      'image_path': 'assets/images/mock/mock_place_01.png',
    });

    expect(place.id, 'place-sensoji');
    expect(place.confidence, 0.92);
    expect(place.toJson()['name'], '아사쿠사 센소지');
  });

  test('TravelPreference serializes enum codes', () {
    const preference = TravelPreference(
      themes: {TravelTheme.photoSpot, TravelTheme.food},
      pace: TravelPace.packed,
    );

    final json = preference.toJson();
    final parsed = TravelPreference.fromJson(json);

    expect(json['themes'], contains('photo_spot'));
    expect(parsed.themes, contains(TravelTheme.food));
    expect(parsed.pace, TravelPace.packed);
  });

  test('AuthProfile round trips account fields', () {
    final profile = AuthProfile.fromJson(const {
      'id': 'user-1',
      'email': 'user@example.com',
      'nickname': '왘왘 여행자',
    });

    expect(profile.id, 'user-1');
    expect(profile.displayName, '왘왘 여행자');
    expect(profile.toJson()['email'], 'user@example.com');
  });
}
