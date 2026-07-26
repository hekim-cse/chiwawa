import 'dart:async';
import 'dart:convert';
// Flutter의 조건부 웹 구현 경계에서만 브라우저 팝업 API를 사용한다.
// ignore: deprecated_member_use, avoid_web_libraries_in_flutter
import 'dart:html' as html;

import '../repositories/auth_repository.dart';

const _successType = 'chiwawa-google-oauth-success';

Future<GoogleAuthResult> openGoogleOAuthPopup({
  required Uri loginUri,
  required String backendOrigin,
}) async {
  final popup = html.window.open(
    loginUri.toString(),
    'chiwawa_google_oauth',
    'popup=yes,width=520,height=720,resizable=yes,scrollbars=yes',
  );
  final completer = Completer<GoogleAuthResult>();
  late final StreamSubscription<html.MessageEvent> subscription;
  Timer? closedWindowTimer;
  DateTime? popupClosedAt;

  subscription = html.window.onMessage.listen((event) {
    if (event.origin != backendOrigin) return;
    final data = event.data;
    if (data is! String) return;
    final decoded = jsonDecode(data);
    if (decoded is! Map || decoded['type'] != _successType) return;
    final payload = decoded['payload'];
    if (payload is! Map) {
      completer.completeError(StateError('로그인 응답 형식이 올바르지 않습니다.'));
      return;
    }
    final result = GoogleAuthResult.fromJson(
      jsonDecode(jsonEncode(payload)) as Map<String, Object?>,
    );
    if (result.accessToken.isEmpty) {
      completer.completeError(StateError('로그인 토큰이 비어 있습니다.'));
      return;
    }
    completer.complete(result);
  });

  closedWindowTimer = Timer.periodic(const Duration(milliseconds: 500), (_) {
    if (completer.isCompleted) return;
    if (popup.closed != true) {
      popupClosedAt = null;
      return;
    }
    popupClosedAt ??= DateTime.now();
    if (DateTime.now().difference(popupClosedAt!) <
        const Duration(seconds: 2)) {
      return;
    }
    completer.completeError(StateError('로그인 창이 완료 전에 닫혔습니다.'));
  });

  try {
    return await completer.future.timeout(const Duration(minutes: 3));
  } finally {
    closedWindowTimer.cancel();
    await subscription.cancel();
    if (popup.closed != true) popup.close();
  }
}
