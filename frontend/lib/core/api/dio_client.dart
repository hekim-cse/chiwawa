import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import 'api_exception.dart';

final apiBaseUrlProvider = Provider<String>(
  (ref) => const String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000',
  ),
);

final dioClientProvider = Provider<Dio>((ref) {
  final baseUrl = ref.watch(apiBaseUrlProvider);
  final apiOrigin = Uri.tryParse(baseUrl);

  final dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 8),
      receiveTimeout: const Duration(seconds: 12),
      sendTimeout: const Duration(seconds: 12),
      headers: const {'Accept': 'application/json'},
    ),
  );

  if (kDebugMode) {
    dio.interceptors.add(
      LogInterceptor(requestBody: true, responseBody: true),
    );
  }

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        final token = ref.read(authTokenProvider);
        if (token != null &&
            token.isNotEmpty &&
            _isSameOrigin(options.uri, apiOrigin)) {
          options.headers['Authorization'] = 'Bearer $token';
        } else if (!_isSameOrigin(options.uri, apiOrigin)) {
          options.headers.remove('Authorization');
        }
        handler.next(options);
      },
      onError: (error, handler) {
        handler.reject(
          DioException(
            requestOptions: error.requestOptions,
            response: error.response,
            type: error.type,
            error: ApiException.fromDioException(error),
            stackTrace: error.stackTrace,
            message: error.message,
          ),
        );
      },
    ),
  );

  return dio;
});

bool _isSameOrigin(Uri request, Uri? apiOrigin) {
  if (apiOrigin == null || !apiOrigin.hasScheme || apiOrigin.host.isEmpty) {
    return false;
  }
  return request.scheme == apiOrigin.scheme &&
      request.host == apiOrigin.host &&
      _effectivePort(request) == _effectivePort(apiOrigin);
}

int _effectivePort(Uri uri) {
  if (uri.hasPort) return uri.port;
  return switch (uri.scheme) {
    'http' => 80,
    'https' => 443,
    _ => -1,
  };
}
