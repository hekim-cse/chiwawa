/// 백엔드 연동 스위치.
/// `flutter run --dart-define=USE_API=true` 로 실행하면 Api 구현체를 사용하고,
/// 기본값(false)은 Mock 구현체로 동작한다. 시연 중 서버 장애 시 플래그만 빼면 복구.
const bool useApiBackend = bool.fromEnvironment('USE_API');

/// 배포 산출물의 원본 Git commit을 확인하기 위한 빌드 메타데이터.
///
/// 배포 파이프라인은 `--dart-define=APP_BUILD_SHA=<40자리 Git SHA>`를 전달한다.
/// 값이 없는 로컬·기존 빌드는 `unknown`으로 표시해 추측한 commit을 노출하지 않는다.
const String appBuildSha = String.fromEnvironment(
  'APP_BUILD_SHA',
  defaultValue: 'unknown',
);
