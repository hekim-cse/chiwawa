import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 인증 상태 3분기: 미선택(로그인 화면) / 둘러보기 / 구글 로그인 완료
enum AuthStatus { signedOut, guest, signedIn }

class AuthUser {
  const AuthUser({this.name, this.email, this.pictureUrl});

  final String? name;
  final String? email;
  final String? pictureUrl;

  String get displayName =>
      (name != null && name!.trim().isNotEmpty) ? name!.trim() : '치와와 여행자';
}

class AuthState {
  const AuthState({
    this.status = AuthStatus.signedOut,
    this.token,
    this.user,
  });

  final AuthStatus status;
  final String? token;
  final AuthUser? user;

  bool get isSignedIn => status == AuthStatus.signedIn;
  bool get isGuest => status == AuthStatus.guest;
}

/// dio 인터셉터가 요청 시점에 읽는 JWT. AuthController만 갱신한다.
final authTokenProvider = StateProvider<String?>((ref) => null);
final authSessionRevisionProvider = StateProvider<int>((ref) => 0);

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) => AuthController(ref)..restore(),
);

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._ref) : super(const AuthState());

  final Ref _ref;
  Future<void>? _restoreTask;
  Future<void> _persistTail = Future<void>.value();
  int _mutationVersion = 0;

  static const _statusKey = 'auth_status';
  static const _tokenKey = 'auth_token';
  static const _nameKey = 'auth_user_name';
  static const _emailKey = 'auth_user_email';
  static const _pictureKey = 'auth_user_picture';

  /// 앱 시작 시 저장된 세션 복원.
  /// 저장소를 못 읽는 환경(위젯 테스트 등)에서도 앱이 죽지 않아야 한다.
  Future<void> restore() => _restoreTask ??= _restore();

  Future<void> get restoreCompleted => _restoreTask ?? Future.value();

  Future<void> _restore() async {
    final restoreVersion = _mutationVersion;
    try {
      final prefs = await SharedPreferences.getInstance();
      final status = prefs.getString(_statusKey);
      final token = prefs.getString(_tokenKey);

      if (!mounted || restoreVersion != _mutationVersion) return;

      if (status == 'signedIn' && token != null && token.isNotEmpty) {
        _ref.read(authTokenProvider.notifier).state = token;
        state = AuthState(
          status: AuthStatus.signedIn,
          token: token,
          user: AuthUser(
            name: prefs.getString(_nameKey),
            email: prefs.getString(_emailKey),
            pictureUrl: prefs.getString(_pictureKey),
          ),
        );
      } else if (status == 'guest') {
        state = AuthState(
          status: AuthStatus.guest,
          user: AuthUser(name: prefs.getString(_nameKey)),
        );
      }
    } catch (_) {
      // 저장소 미지원 환경에서는 복원 없이 signedOut으로 시작
    }
  }

  /// 구글 로그인 성공 처리 — 딥링크 복귀(실서버) 또는 Mock 로그인에서 호출
  Future<void> signInWithToken(String token, {AuthUser? user}) async {
    _advanceSessionIfChanged(AuthStatus.signedIn, token);
    _mutationVersion += 1;
    _ref.read(authTokenProvider.notifier).state = token;
    state = AuthState(status: AuthStatus.signedIn, token: token, user: user);
    await _persist();
  }

  Future<void> continueAsGuest() async {
    _advanceSessionIfChanged(AuthStatus.guest, null);
    _mutationVersion += 1;
    _ref.read(authTokenProvider.notifier).state = null;
    state = const AuthState(status: AuthStatus.guest);
    await _persist();
  }

  Future<void> signOut() async {
    _advanceSessionIfChanged(AuthStatus.signedOut, null);
    _mutationVersion += 1;
    _ref.read(authTokenProvider.notifier).state = null;
    state = const AuthState();
    await _persist();
  }

  Future<void> updateDisplayName(String name) async {
    final trimmed = name.trim();
    if (trimmed.isEmpty) return;
    _mutationVersion += 1;
    final currentUser = state.user;
    state = AuthState(
      status: state.status,
      token: state.token,
      user: AuthUser(
        name: trimmed,
        email: currentUser?.email,
        pictureUrl: currentUser?.pictureUrl,
      ),
    );
    await _persist();
  }

  Future<void> _persist() {
    final snapshot = state;
    final operation = _persistTail.then((_) => _writeSnapshot(snapshot));
    _persistTail = operation;
    return operation;
  }

  Future<void> _writeSnapshot(AuthState current) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      switch (current.status) {
        case AuthStatus.signedIn:
          await prefs.setString(_statusKey, 'signedIn');
          await prefs.setString(_tokenKey, current.token ?? '');
          await prefs.setString(_nameKey, current.user?.name ?? '');
          await prefs.setString(_emailKey, current.user?.email ?? '');
          await prefs.setString(_pictureKey, current.user?.pictureUrl ?? '');
        case AuthStatus.guest:
          await prefs.setString(_statusKey, 'guest');
          await prefs.setString(_nameKey, current.user?.name ?? '');
          await prefs.remove(_tokenKey);
          await prefs.remove(_emailKey);
          await prefs.remove(_pictureKey);
        case AuthStatus.signedOut:
          await prefs.remove(_statusKey);
          await prefs.remove(_tokenKey);
          await prefs.remove(_nameKey);
          await prefs.remove(_emailKey);
          await prefs.remove(_pictureKey);
      }
    } catch (_) {
      // 저장 실패는 세션 유지에만 영향 — 현재 실행 중 상태는 정상 동작
    }
  }

  void _advanceSessionIfChanged(AuthStatus nextStatus, String? nextToken) {
    if (state.status == nextStatus && state.token == nextToken) return;
    final revision = _ref.read(authSessionRevisionProvider.notifier);
    revision.state += 1;
  }
}
