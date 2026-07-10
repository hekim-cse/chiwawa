import 'package:dio/dio.dart';

import '../../api/api_exception.dart';
import '../auth_repository.dart';

/// chiwawa_backend 인증 구현체.
/// 구글 동의 화면은 GET /api/v1/auth/google/login에서 시작하고,
/// 앱이 OAuth code를 확보하면 callback API로 JWT를 교환한다.
class ApiAuthRepository implements AuthRepository {
  const ApiAuthRepository({required this.dio});

  final Dio dio;

  @override
  Future<AuthProfile> signIn({
    required String email,
    required String password,
  }) async {
    // 백엔드에 이메일/비밀번호 로그인 API 없음 — 구글 로그인만 지원
    throw const ApiException('구글 로그인으로 이용해 주세요.');
  }

  @override
  Future<AuthProfile> signUp({
    required String nickname,
    required String email,
    required String password,
  }) async {
    throw const ApiException('구글 로그인으로 이용해 주세요.');
  }

  @override
  Future<AuthProfile> fetchMe() async {
    // Authorization 헤더는 dio 인터셉터가 자동 첨부
    try {
      final response = await dio.get<Map<String, Object?>>('/api/v1/auth/me');
      final json = response.data ?? const {};
      return AuthProfile(
        id: json['sub']?.toString() ?? '',
        email: json['email'] as String? ?? '',
        displayName: json['name'] as String? ?? '',
      );
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  @override
  Future<GoogleAuthResult> signInWithGoogleCode(
    String code, {
    String? state,
  }) async {
    try {
      final query = <String, Object?>{'code': code};
      if (state != null && state.isNotEmpty) {
        query['state'] = state;
      }

      final response = await dio.get<Map<String, Object?>>(
        '/api/v1/auth/google/callback',
        queryParameters: query,
      );
      final result = GoogleAuthResult.fromJson(response.data ?? const {});
      if (result.accessToken.isEmpty) {
        throw const ApiException('로그인에 실패했어요. 다시 시도해 주세요.');
      }
      return result;
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }
}
