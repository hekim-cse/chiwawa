import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/dio_client.dart';
import '../env.dart';
import 'api/api_auth_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  if (useApiBackend) {
    return ApiAuthRepository(dio: ref.watch(dioClientProvider));
  }
  return const MockAuthRepository();
});

abstract class AuthRepository {
  Future<AuthProfile> signIn({
    required String email,
    required String password,
  });

  Future<AuthProfile> signUp({
    required String nickname,
    required String email,
    required String password,
  });

  /// JWT로 내 정보 조회 (백엔드 GET /api/v1/auth/me) — 앱 시작/복귀 후 토큰 검증용
  Future<AuthProfile> fetchMe();

  /// OAuth code → JWT 교환 (GET /api/v1/auth/google/callback?code=...)
  Future<GoogleAuthResult> signInWithGoogleCode(String code, {String? state});
}

class GoogleAuthResult {
  const GoogleAuthResult({
    required this.accessToken,
    required this.profile,
    this.pictureUrl,
  });

  final String accessToken;
  final AuthProfile profile;
  final String? pictureUrl;

  /// 백엔드 callback 응답 { user: {...}, access_token } 파싱
  factory GoogleAuthResult.fromJson(Map<String, Object?> json) {
    final user = json['user'] as Map<String, Object?>? ?? const {};
    return GoogleAuthResult(
      accessToken: json['access_token'] as String? ?? '',
      profile: AuthProfile(
        id: user['id']?.toString() ?? '',
        email: user['email'] as String? ?? '',
        displayName: user['name'] as String? ?? '',
      ),
      pictureUrl: user['picture'] as String?,
    );
  }
}

class AuthProfile {
  const AuthProfile({
    required this.email,
    required this.displayName,
    this.id = '',
  });

  final String email;
  final String displayName;
  final String id;

  factory AuthProfile.fromJson(Map<String, Object?> json) {
    return AuthProfile(
      id: json['id']?.toString() ?? json['sub']?.toString() ?? '',
      email: json['email'] as String? ?? '',
      displayName: json['name'] as String? ??
          json['nickname'] as String? ??
          json['display_name'] as String? ??
          '',
    );
  }

  Map<String, Object?> toJson() {
    return {
      'id': id,
      'email': email,
      'nickname': displayName,
    };
  }
}

class MockAuthRepository implements AuthRepository {
  const MockAuthRepository();

  @override
  Future<AuthProfile> signIn({
    required String email,
    required String password,
  }) async {
    return AuthProfile(email: email, displayName: '치와와 여행자');
  }

  @override
  Future<AuthProfile> signUp({
    required String nickname,
    required String email,
    required String password,
  }) async {
    return AuthProfile(email: email, displayName: nickname);
  }

  @override
  Future<AuthProfile> fetchMe() async {
    return const AuthProfile(
      email: 'traveler@chiwawa.app',
      displayName: '치와와 여행자',
    );
  }

  @override
  Future<GoogleAuthResult> signInWithGoogleCode(
    String code, {
    String? state,
  }) async {
    return const GoogleAuthResult(
      accessToken: 'mock-jwt-token',
      profile: AuthProfile(
        email: 'traveler@chiwawa.app',
        displayName: '치와와 여행자',
      ),
    );
  }
}
