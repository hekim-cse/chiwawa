import '../repositories/auth_repository.dart';

Future<GoogleAuthResult> openGoogleOAuthPopup({
  required Uri loginUri,
  required String backendOrigin,
}) {
  throw UnsupportedError('OAuth 팝업은 웹에서만 지원합니다.');
}
