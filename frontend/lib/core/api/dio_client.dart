import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import 'api_exception.dart';

/// Modal 연동처럼 응답 시간이 외부 서비스에 의해 결정되는 요청임을 표시한다.
const waitForServerResponseExtraKey = 'wait_for_server_response';

/// 연결·전송·수신 단계에 프론트 timeout을 두지 않는 요청 옵션이다.
Options waitForServerResponseOptions() => Options(
      sendTimeout: Duration.zero,
      receiveTimeout: Duration.zero,
      extra: const {waitForServerResponseExtraKey: true},
    );

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

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        if (options.extra[waitForServerResponseExtraKey] == true) {
          // BrowserHttpClientAdapter에서는 응답이 늦을 때도 connectionTimeout으로
          // 보고될 수 있으므로 장기 실행 요청은 세 단계 모두 명시적으로 해제한다.
          options.connectTimeout = Duration.zero;
          options.sendTimeout = Duration.zero;
          options.receiveTimeout = Duration.zero;
        }
        handler.next(options);
      },
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
