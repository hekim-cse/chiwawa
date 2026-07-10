import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../repositories/auth_repository.dart';
import 'auth_controller.dart';

/// 구글 로그인 후 앱 복귀 딥링크 처리.
/// 계약 기준으로는 토큰을 딥링크로 직접 받지 않고, OAuth code를 받은 뒤
/// GET /api/v1/auth/google/callback?code=... 으로 JWT를 교환한다.
final deepLinkServiceProvider = Provider<DeepLinkService>((ref) {
  final service = DeepLinkService(ref);
  ref.onDispose(service.dispose);
  return service;
});

class DeepLinkService {
  DeepLinkService(this._ref);

  final Ref _ref;
  StreamSubscription<Uri>? _subscription;
  bool _started = false;

  /// 앱 시작 시 1회 호출. 플랫폼 채널 미지원 환경(위젯 테스트)에서도 안전.
  Future<void> start() async {
    if (_started) return;
    _started = true;

    try {
      final appLinks = AppLinks();

      final initial = await appLinks.getInitialLink();
      if (initial != null) {
        await handleAuthRedirect(initial);
      }

      _subscription = appLinks.uriLinkStream.listen(
        (uri) => unawaited(handleAuthRedirect(uri)),
        onError: (_) {},
      );
    } catch (_) {
      // 딥링크 미지원 환경 — 로그인 화면의 Mock 플로우는 영향 없음
    }
  }

  /// 계약(docs/auth-google-jwt-contract.md) 기준:
  /// 앱은 OAuth `code`를 딥링크로 받고, callback API로 JWT를 교환한다.
  /// 토큰을 딥링크로 직접 받는 방식은 계약에 없으므로 처리하지 않는다.
  Future<bool> handleAuthRedirect(Uri uri) async {
    if (uri.scheme != 'chiwawa' || uri.host != 'auth') return false;

    final code = uri.queryParameters['code'];
    if (code == null || code.isEmpty) return false;

    try {
      final result =
          await _ref.read(authRepositoryProvider).signInWithGoogleCode(
                code,
                state: uri.queryParameters['state'],
              );

      await _ref.read(authControllerProvider.notifier).signInWithToken(
            result.accessToken,
            user: AuthUser(
              name: result.profile.displayName,
              email: result.profile.email,
              pictureUrl: result.pictureUrl,
            ),
          );
      return true;
    } catch (_) {
      // 교환 실패 — 로그인 화면 유지, 사용자가 재시도 가능
      return false;
    }
  }

  void dispose() {
    _subscription?.cancel();
  }
}
