/// 백엔드 연동 스위치.
/// `flutter run --dart-define=USE_API=true` 로 실행하면 Api 구현체를 사용하고,
/// 기본값(false)은 Mock 구현체로 동작한다. 시연 중 서버 장애 시 플래그만 빼면 복구.
const bool useApiBackend = bool.fromEnvironment('USE_API');
