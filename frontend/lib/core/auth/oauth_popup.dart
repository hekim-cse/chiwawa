import '../repositories/auth_repository.dart';
import 'oauth_popup_stub.dart' if (dart.library.html) 'oauth_popup_web.dart'
    as implementation;

Future<GoogleAuthResult> openGoogleOAuthPopup({
  required Uri loginUri,
  required String backendOrigin,
}) {
  return implementation.openGoogleOAuthPopup(
    loginUri: loginUri,
    backendOrigin: backendOrigin,
  );
}
