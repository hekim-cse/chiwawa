import 'package:flutter_riverpod/flutter_riverpod.dart';

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => const MockAuthRepository(),
);

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
      id: json['id']?.toString() ?? '',
      email: json['email'] as String? ?? '',
      displayName:
          json['nickname'] as String? ?? json['display_name'] as String? ?? '',
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
}
