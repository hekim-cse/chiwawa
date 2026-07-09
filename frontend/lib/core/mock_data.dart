import 'assets/app_images.dart';
import 'models/travel_models.dart';

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

const routePlaces = [
  RoutePlace(
    name: '메이지 신궁',
    duration: '90분',
    transport: '지하철 12분',
    category: '신사',
  ),
  RoutePlace(
    name: '하라주쿠 다케시타도리',
    duration: '60분',
    transport: '도보 8분',
    category: '쇼핑',
  ),
  RoutePlace(
    name: '오모테산도',
    duration: '120분',
    transport: '도보 5분',
    category: '카페·거리',
  ),
  RoutePlace(
    name: '시부야 스크램블',
    duration: '60분',
    transport: '지하철 7분',
    category: '랜드마크',
  ),
];

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
];

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
