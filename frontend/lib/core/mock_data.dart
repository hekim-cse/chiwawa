class TripInfo {
  const TripInfo({
    required this.tripName,
    required this.period,
    required this.currentDay,
    required this.members,
    required this.city,
    required this.weather,
  });

  final String tripName;
  final String period;
  final String currentDay;
  final int members;
  final String city;
  final String weather;
}

class ScheduleItem {
  const ScheduleItem({
    required this.time,
    this.place,
    this.transport = '',
    this.freeMinutes,
    required this.status,
  });

  final String time;
  final String? place;
  final String transport;
  final int? freeMinutes;
  final ScheduleStatus status;
}

enum ScheduleStatus { completed, ongoing, free, upcoming }

class RoutePlace {
  const RoutePlace({
    required this.name,
    required this.duration,
    required this.transport,
    required this.category,
  });

  final String name;
  final String duration;
  final String transport;
  final String category;
}

class FreeTimeRecommend {
  const FreeTimeRecommend({
    required this.name,
    required this.walk,
    required this.duration,
  });

  final String name;
  final String walk;
  final String duration;
}

class PhotoSearchResult {
  const PhotoSearchResult({
    required this.name,
    required this.address,
    required this.category,
  });

  final String name;
  final String address;
  final String category;
}

class MemorialSummary {
  const MemorialSummary({
    required this.days,
    required this.places,
    required this.distance,
  });

  final int days;
  final int places;
  final String distance;
}

class MemorialDay {
  const MemorialDay({
    required this.date,
    required this.places,
    required this.photos,
  });

  final String date;
  final List<String> places;
  final int photos;
}

const tripInfo = TripInfo(
  tripName: '도쿄 봄 여행',
  period: '2025.04.01 ~ 04.04',
  currentDay: '3일차',
  members: 2,
  city: '도쿄, 일본',
  weather: '18°C 맑음',
);

const schedules = [
  ScheduleItem(
    time: '09:00',
    place: '아사쿠사 센소지',
    transport: '도보',
    status: ScheduleStatus.ongoing,
  ),
  ScheduleItem(
    time: '12:00',
    place: '스카이트리',
    transport: '지하철',
    status: ScheduleStatus.upcoming,
  ),
  ScheduleItem(
    time: '13:30',
    freeMinutes: 60,
    status: ScheduleStatus.free,
  ),
  ScheduleItem(
    time: '15:00',
    place: '시부야 스크램블 교차로',
    transport: '지하철',
    status: ScheduleStatus.upcoming,
  ),
  ScheduleItem(
    time: '18:00',
    place: '신주쿠 맛집 거리',
    transport: '지하철',
    status: ScheduleStatus.upcoming,
  ),
  ScheduleItem(
    time: '20:00',
    place: '도쿄 타워 야경',
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
  name: '아사쿠사 센소지',
  address: '도쿄 다이토구 아사쿠사 2-3-1',
  category: '사찰·관광지',
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
  MemorialDay(date: '4월 1일', places: ['나리타 공항', '아사쿠사', '신주쿠'], photos: 34),
  MemorialDay(date: '4월 2일', places: ['우에노', '아키하바라', '시부야'], photos: 52),
  MemorialDay(date: '4월 3일', places: ['하라주쿠', '오모테산도', '롯폰기'], photos: 41),
];

const recentSearches = [
  PhotoSearchResult(
    name: '도쿄 타워',
    address: '일본 도쿄 미나토구 시바코엔 4-2-8',
    category: '전망대',
  ),
  PhotoSearchResult(
    name: '메구로강',
    address: '일본 도쿄 메구로구',
    category: '벚꽃 명소',
  ),
  PhotoSearchResult(
    name: '우에노 공원',
    address: '일본 도쿄 다이토구',
    category: '공원',
  ),
];
