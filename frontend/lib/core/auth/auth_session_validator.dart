import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_exception.dart';
import '../env.dart';
import '../repositories/auth_repository.dart';
import 'auth_controller.dart';

final authSessionValidatorProvider = Provider<AuthSessionValidator>(
  (ref) => AuthSessionValidator(ref),
);

class AuthSessionValidator {
  const AuthSessionValidator(this._ref);

  final Ref _ref;

  /// 저장된 JWT가 있으면 /api/v1/auth/me로 검증하고 사용자 정보를 복구한다.
  /// Mock 모드에서는 발표/테스트 안정성을 위해 로컬 복원만 사용한다.
  Future<void> validateRestoredSession() async {
    await _ref.read(authControllerProvider.notifier).restoreCompleted;
    if (!useApiBackend) return;

    final auth = _ref.read(authControllerProvider);
    final token = auth.token;
    if (!auth.isSignedIn || token == null || token.isEmpty) return;

    try {
      final profile = await _ref.read(authRepositoryProvider).fetchMe();
      await _ref.read(authControllerProvider.notifier).signInWithToken(
            token,
            user: AuthUser(
              name: profile.displayName,
              email: profile.email,
              pictureUrl: auth.user?.pictureUrl,
            ),
          );
    } on ApiException catch (error) {
      if (error.statusCode == 401) {
        await _ref.read(authControllerProvider.notifier).signOut();
      }
    } catch (_) {
      // 네트워크 일시 오류는 저장 세션을 즉시 삭제하지 않는다.
    }
  }
}
