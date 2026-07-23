import 'assets/app_images.dart';
import 'models/memorial_map_models.dart';
import 'models/transport_mode.dart';
import 'models/travel_models.dart';

const trips = [
  Trip(
    id: 'trip-tokyo-spring',
    title: '도쿄 봄 여행',
    city: '도쿄',
    country: '일본',
    startDate: '2025-04-01',
    endDate: '2025-04-04',
    travelers: 2,
    interests: ['photo_spot', 'culture'],
    travelStyle: TravelPace.balanced,
  ),
  Trip(
    id: 'trip-osaka-food',
    title: '오사카 맛집 여행',
    city: '오사카',
    country: '일본',
    startDate: '2025-08-15',
    endDate: '2025-08-18',
    travelers: 3,
    interests: ['food', 'shopping'],
    travelStyle: TravelPace.packed,
  ),
  Trip(
    id: 'trip-kyoto-autumn',
    title: '교토 가을 산책',
    city: '교토',
    country: '일본',
    startDate: '2025-11-06',
    endDate: '2025-11-09',
    travelers: 1,
    interests: ['culture', 'photo_spot'],
    travelStyle: TravelPace.relaxed,
  ),
];

const tripInfo = TripInfo(
  tripId: 'trip-tokyo-spring',
  tripName: '도쿄 봄 여행',
  period: '2025.04.01 ~ 04.04',
  currentDay: '3일차',
  members: 2,
  city: '도쿄, 일본',
  weather: '18°C 맑음',
);

const schedules = [
  ScheduleItem(
    id: 'schedule-sensoji',
    tripId: 'trip-tokyo-spring',
    date: '2025-04-03',
    startTime: '09:00',
    endTime: '10:30',
    name: '아사쿠사 센소지',
    placeId: 'place-sensoji',
    source: 'mock',
    transport: '도보',
    status: ScheduleStatus.ongoing,
  ),
  ScheduleItem(
    id: 'schedule-skytree',
    tripId: 'trip-tokyo-spring',
    date: '2025-04-03',
    startTime: '12:00',
    endTime: '13:00',
    name: '스카이트리',
    placeId: 'place-skytree',
    source: 'mock',
    transport: '지하철',
    status: ScheduleStatus.upcoming,
  ),
  ScheduleItem(
    id: 'schedule-free-1',
    tripId: 'trip-tokyo-spring',
    date: '2025-04-03',
    startTime: '13:30',
    endTime: '14:30',
    source: 'mock',
    freeMinutes: 60,
    status: ScheduleStatus.free,
  ),
  ScheduleItem(
    id: 'schedule-shibuya',
    tripId: 'trip-tokyo-spring',
    date: '2025-04-03',
    startTime: '15:00',
    endTime: '16:00',
    name: '시부야 스크램블 교차로',
    placeId: 'place-shibuya-crossing',
    source: 'mock',
    transport: '지하철',
    status: ScheduleStatus.upcoming,
  ),
  ScheduleItem(
    id: 'schedule-shinjuku',
    tripId: 'trip-tokyo-spring',
    date: '2025-04-03',
    startTime: '18:00',
    endTime: '19:30',
    name: '신주쿠 맛집 거리',
    placeId: 'place-shinjuku-food',
    source: 'mock',
    transport: '지하철',
    status: ScheduleStatus.upcoming,
  ),
  ScheduleItem(
    id: 'schedule-tokyo-tower',
    tripId: 'trip-tokyo-spring',
    date: '2025-04-03',
    startTime: '20:00',
    endTime: '21:00',
    name: '도쿄 타워 야경',
    placeId: 'place-tokyo-tower',
    source: 'mock',
    transport: '도보',
    status: ScheduleStatus.upcoming,
  ),
];

const freeTimeRecommends = [
  FreeTimeRecommend(name: '아메요코 시장', walk: '8분', duration: '45분'),
  FreeTimeRecommend(name: '도쿄국립박물관', walk: '5분', duration: '60분'),
  FreeTimeRecommend(name: '야나카 긴자 상점가', walk: '12분', duration: '50분'),
];

const photoSearchResult = PhotoSearchResult(
  id: 'place-sensoji',
  name: '아사쿠사 센소지',
  address: '도쿄 다이토구 아사쿠사 2-3-1',
  category: '사찰·관광지',
  latitude: 35.7148,
  longitude: 139.7967,
  confidence: 0.92,
  imagePath: MockImages.mockPlace01,
);

const photoSearchCandidates = [
  photoSearchResult,
  PhotoSearchResult(
    id: 'place-kaminarimon',
    name: '가미나리몬',
    address: '도쿄 다이토구 아사쿠사 2-3-1',
    category: '문·랜드마크',
    latitude: 35.7111,
    longitude: 139.7964,
    confidence: 0.78,
    imagePath: MockImages.mockPlace02,
  ),
  PhotoSearchResult(
    id: 'place-asakusa-shrine',
    name: '아사쿠사 신사',
    address: '도쿄 다이토구 아사쿠사 2-3-1',
    category: '신사',
    latitude: 35.7149,
    longitude: 139.7974,
    confidence: 0.64,
    imagePath: MockImages.mockPlace03,
  ),
];

const transitRoutePlaces = [
  RoutePlace(
    name: '메이지 신궁',
    duration: '90분',
    transport: '지하철 12분',
    category: '신사',
    travelCost: '¥180',
  ),
  RoutePlace(
    name: '하라주쿠 다케시타도리',
    duration: '60분',
    transport: '도보 8분',
    category: '쇼핑',
    travelCost: '무료',
  ),
  RoutePlace(
    name: '오모테산도',
    duration: '120분',
    transport: '도보 5분',
    category: '카페·거리',
    travelCost: '무료',
  ),
  RoutePlace(
    name: '시부야 스크램블',
    duration: '60분',
    transport: '지하철 7분',
    category: '랜드마크',
    travelCost: '¥150',
  ),
];

const walkRoutePlaces = [
  RoutePlace(
    name: '메이지 신궁',
    duration: '90분',
    transport: '도보 0분',
    category: '신사',
    travelCost: '무료',
  ),
  RoutePlace(
    name: '하라주쿠 다케시타도리',
    duration: '55분',
    transport: '도보 14분',
    category: '쇼핑',
    travelCost: '무료',
  ),
  RoutePlace(
    name: '오모테산도',
    duration: '100분',
    transport: '도보 12분',
    category: '카페·거리',
    travelCost: '무료',
  ),
  RoutePlace(
    name: '시부야 스크램블',
    duration: '60분',
    transport: '도보 18분',
    category: '랜드마크',
    travelCost: '무료',
  ),
];

const driveRoutePlaces = [
  RoutePlace(
    name: '메이지 신궁',
    duration: '80분',
    transport: '자동차 0분',
    category: '신사',
    travelCost: '무료',
  ),
  RoutePlace(
    name: '시부야 스크램블',
    duration: '50분',
    transport: '자동차 11분',
    category: '랜드마크',
    travelCost: '¥700',
  ),
  RoutePlace(
    name: '오모테산도',
    duration: '90분',
    transport: '자동차 9분',
    category: '카페·거리',
    travelCost: '¥500',
  ),
  RoutePlace(
    name: '하라주쿠 다케시타도리',
    duration: '55분',
    transport: '자동차 7분',
    category: '쇼핑',
    travelCost: '¥400',
  ),
];

List<RoutePlace> routePlacesFor(TransportMode mode) {
  return switch (mode) {
    TransportMode.walk => walkRoutePlaces,
    TransportMode.drive => driveRoutePlaces,
    TransportMode.transit => transitRoutePlaces,
  };
}

const memorialSummary =
    MemorialSummary(days: 4, places: 12, distance: '38.4km');

const memorialDays = [
  MemorialDay(
    date: '4월 1일',
    places: ['나리타 공항', '아사쿠사', '신주쿠'],
    photos: 34,
    photoAssetPaths: [
      MockImages.mockMemorial01,
      MockImages.mockMemorial02,
      MockImages.mockMemorial03,
    ],
  ),
  MemorialDay(
    date: '4월 2일',
    places: ['우에노', '아키하바라', '시부야'],
    photos: 52,
    photoAssetPaths: [
      MockImages.mockMemorial02,
      MockImages.mockMemorial03,
      MockImages.mockMemorial01,
    ],
  ),
  MemorialDay(
    date: '4월 3일',
    places: ['하라주쿠', '오모테산도', '롯폰기'],
    photos: 41,
    photoAssetPaths: [
      MockImages.mockMemorial03,
      MockImages.mockMemorial01,
      MockImages.mockMemorial02,
    ],
  ),
  MemorialDay(
    date: '4월 4일',
    places: ['도쿄 타워', '긴자', '도쿄역'],
    photos: 28,
    photoAssetPaths: [
      MockImages.mockMemorial01,
      MockImages.mockMemorial03,
      MockImages.mockMemorial02,
    ],
  ),
];

final memorialTripDates = List<DateTime>.unmodifiable([
  DateTime(2025, 4, 1),
  DateTime(2025, 4, 2),
  DateTime(2025, 4, 3),
  DateTime(2025, 4, 4),
]);

final memorialPhotoPoints = List<MemorialPhotoPoint>.unmodifiable([
  MemorialPhotoPoint(
    id: 'photo-0401-narita-1',
    takenAt: DateTime(2025, 4, 1, 9, 20),
    latitude: 35.7719,
    longitude: 140.3929,
    placeName: '나리타 공항',
    assetPath: MockImages.mockMemorial01,
  ),
  MemorialPhotoPoint(
    id: 'photo-0401-asakusa-1',
    takenAt: DateTime(2025, 4, 1, 12, 10),
    latitude: 35.7148,
    longitude: 139.7967,
    placeName: '아사쿠사 센소지',
    assetPath: MockImages.mockMemorial02,
  ),
  MemorialPhotoPoint(
    id: 'photo-0401-asakusa-2',
    takenAt: DateTime(2025, 4, 1, 12, 28),
    latitude: 35.7149,
    longitude: 139.7968,
    placeName: '아사쿠사 센소지',
    assetPath: MockImages.mockMemorial03,
  ),
  MemorialPhotoPoint(
    id: 'photo-0401-shinjuku-1',
    takenAt: DateTime(2025, 4, 1, 18, 30),
    latitude: 35.6938,
    longitude: 139.7034,
    placeName: '신주쿠',
    assetPath: MockImages.mockMemorial01,
  ),
  MemorialPhotoPoint(
    id: 'photo-0402-ueno-1',
    takenAt: DateTime(2025, 4, 2, 9, 40),
    latitude: 35.7156,
    longitude: 139.7745,
    placeName: '우에노 공원',
    assetPath: MockImages.mockMemorial02,
  ),
  MemorialPhotoPoint(
    id: 'photo-0402-akihabara-1',
    takenAt: DateTime(2025, 4, 2, 12, 10),
    latitude: 35.6984,
    longitude: 139.7730,
    placeName: '아키하바라',
    assetPath: MockImages.mockMemorial03,
  ),
  MemorialPhotoPoint(
    id: 'photo-0402-shibuya-1',
    takenAt: DateTime(2025, 4, 2, 16, 20),
    latitude: 35.6595,
    longitude: 139.7005,
    placeName: '시부야 스크램블',
    assetPath: MockImages.mockMemorial01,
  ),
  MemorialPhotoPoint(
    id: 'photo-0402-shibuya-2',
    takenAt: DateTime(2025, 4, 2, 16, 33),
    latitude: 35.6596,
    longitude: 139.7006,
    placeName: '시부야 스크램블',
    assetPath: MockImages.mockMemorial02,
  ),
  MemorialPhotoPoint(
    id: 'photo-0403-harajuku-1',
    takenAt: DateTime(2025, 4, 3, 10, 10),
    latitude: 35.6716,
    longitude: 139.7026,
    placeName: '하라주쿠',
    assetPath: MockImages.mockMemorial03,
  ),
  MemorialPhotoPoint(
    id: 'photo-0403-omotesando-1',
    takenAt: DateTime(2025, 4, 3, 13, 5),
    latitude: 35.6652,
    longitude: 139.7120,
    placeName: '오모테산도',
    assetPath: MockImages.mockMemorial01,
  ),
  MemorialPhotoPoint(
    id: 'photo-0403-roppongi-1',
    takenAt: DateTime(2025, 4, 3, 18, 40),
    latitude: 35.6627,
    longitude: 139.7314,
    placeName: '롯폰기',
    assetPath: MockImages.mockMemorial02,
  ),
  MemorialPhotoPoint(
    id: 'photo-0403-tower-1',
    takenAt: DateTime(2025, 4, 3, 20, 10),
    latitude: 35.6586,
    longitude: 139.7454,
    placeName: '도쿄 타워',
    assetPath: MockImages.mockMemorial03,
  ),
  MemorialPhotoPoint(
    id: 'photo-0404-ginza-1',
    takenAt: DateTime(2025, 4, 4, 10, 25),
    latitude: 35.6719,
    longitude: 139.7650,
    placeName: '긴자',
    assetPath: MockImages.mockMemorial01,
  ),
  MemorialPhotoPoint(
    id: 'photo-0404-tokyo-station-1',
    takenAt: DateTime(2025, 4, 4, 13, 0),
    latitude: 35.6812,
    longitude: 139.7671,
    placeName: '도쿄역',
    assetPath: MockImages.mockMemorial02,
  ),
  MemorialPhotoPoint(
    id: 'photo-0404-marunouchi-1',
    takenAt: DateTime(2025, 4, 4, 14, 35),
    latitude: 35.6815,
    longitude: 139.7639,
    placeName: '마루노우치',
    assetPath: MockImages.mockMemorial03,
  ),
]);

const recentSearches = [
  PhotoSearchResult(
    id: 'place-tokyo-tower',
    name: '도쿄 타워',
    address: '일본 도쿄 미나토구 시바코엔 4-2-8',
    category: '전망대',
    imagePath: MockImages.mockPlace03,
  ),
  PhotoSearchResult(
    id: 'place-meguro-river',
    name: '메구로강',
    address: '일본 도쿄 메구로구',
    category: '벚꽃 명소',
    imagePath: MockImages.mockPlace02,
  ),
  PhotoSearchResult(
    id: 'place-ueno-park',
    name: '우에노 공원',
    address: '일본 도쿄 다이토구',
    category: '공원',
    imagePath: MockImages.mockPlace01,
  ),
];
