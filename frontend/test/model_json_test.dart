import 'package:flutter_test/flutter_test.dart';
import 'package:chiwawa/core/models/travel_models.dart';
import 'package:chiwawa/core/repositories/auth_repository.dart';

void main() {
  test('Trip parses backend fields and TripDraft serializes create request',
      () {
    final trip = Trip.fromJson(const {
      'id': 'trip-1',
      'title': '도쿄 봄 여행',
      'city': 'Tokyo',
      'country': 'Japan',
      'start_date': '2026-04-01',
      'end_date': '2026-04-04',
      'travelers': 2,
      'interests': ['photo_spot', 'food'],
      'travel_style': 'balanced',
    });
    const draft = TripDraft(
      title: '오사카 여행',
      city: 'Osaka',
      startDate: '2026-05-01',
      endDate: '2026-05-03',
      travelers: 3,
      interests: ['food'],
      travelStyle: TravelPace.packed,
    );

    expect(trip.id, 'trip-1');
    expect(trip.travelers, 2);
    expect(trip.travelStyle, TravelPace.balanced);
    expect(trip.toTripInfo(today: DateTime(2026, 4, 2)).currentDay, '2일차');
    expect(draft.toJson()['travel_style'], 'packed');
    expect(draft.toJson()['country'], 'Japan');
  });

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
      'name': '왘왘 여행자',
    });

    expect(profile.id, 'user-1');
    expect(profile.displayName, '왘왘 여행자');
    expect(profile.toJson()['email'], 'user@example.com');
  });

  test('AuthProfile parses auth me response fields', () {
    final profile = AuthProfile.fromJson(const {
      'sub': 'google-user-1',
      'email': 'user@gmail.com',
      'name': 'Google User',
    });

    expect(profile.id, 'google-user-1');
    expect(profile.email, 'user@gmail.com');
    expect(profile.displayName, 'Google User');
  });

  test('GoogleAuthResult parses callback contract', () {
    final result = GoogleAuthResult.fromJson(const {
      'access_token': 'jwt-token',
      'user': {
        'id': 'user-1',
        'google_sub': 'google-sub',
        'email': 'user@gmail.com',
        'name': 'Google User',
        'picture': 'https://lh3.googleusercontent.com/avatar.png',
      },
    });

    expect(result.accessToken, 'jwt-token');
    expect(result.profile.id, 'user-1');
    expect(result.profile.displayName, 'Google User');
    expect(result.pictureUrl, contains('googleusercontent.com'));
  });
}
