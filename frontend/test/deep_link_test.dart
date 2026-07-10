import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:chiwawa/core/auth/auth_controller.dart';
import 'package:chiwawa/core/auth/deep_link_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  ProviderContainer makeContainer() {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    return container;
  }

  test('계약에 없는 token 직접 전달은 무시한다', () async {
    final container = makeContainer();

    final handled = await container
        .read(deepLinkServiceProvider)
        .handleAuthRedirect(Uri.parse('chiwawa://auth?token=jwt-abc'));

    expect(handled, isFalse);
    expect(
      container.read(authControllerProvider).status,
      AuthStatus.signedOut,
    );
    expect(container.read(authTokenProvider), isNull);
  });

  test('계약 기준: code 딥링크 수신 시 callback 교환 후 로그인된다', () async {
    final container = makeContainer();

    final handled =
        await container.read(deepLinkServiceProvider).handleAuthRedirect(
              Uri.parse('chiwawa://auth?code=oauth-code&state=csrf'),
            );

    expect(handled, isTrue);
    final auth = container.read(authControllerProvider);
    expect(auth.status, AuthStatus.signedIn);
    expect(auth.token, 'mock-jwt-token');
    expect(auth.user?.email, 'traveler@chiwawa.app');
  });

  test('무관한 URI는 무시하고 로그아웃 상태를 유지한다', () async {
    final container = makeContainer();

    final handled = await container
        .read(deepLinkServiceProvider)
        .handleAuthRedirect(Uri.parse('https://example.com/?token=x'));

    expect(handled, isFalse);
    expect(
      container.read(authControllerProvider).status,
      AuthStatus.signedOut,
    );
  });

  test('token도 code도 없는 auth URI는 처리하지 않는다', () async {
    final container = makeContainer();

    final handled = await container
        .read(deepLinkServiceProvider)
        .handleAuthRedirect(Uri.parse('chiwawa://auth'));

    expect(handled, isFalse);
    expect(
      container.read(authControllerProvider).status,
      AuthStatus.signedOut,
    );
  });
}
