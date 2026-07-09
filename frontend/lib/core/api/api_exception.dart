import 'package:dio/dio.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  bool get isNotFound => statusCode == 404;

  factory ApiException.fromDioException(DioException error) {
    final statusCode = error.response?.statusCode;
    final detail = _extractDetail(error.response?.data);

    if (detail != null) {
      return ApiException(detail, statusCode: statusCode);
    }

    return ApiException(
      _fallbackMessageFor(error),
      statusCode: statusCode,
    );
  }

  @override
  String toString() => message;
}

String mapApiErrorToMessage(Object error) {
  if (error is ApiException) return error.message;
  if (error is DioException) {
    final apiError = error.error;
    if (apiError is ApiException) return apiError.message;
    return ApiException.fromDioException(error).message;
  }
  return '요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.';
}

String? _extractDetail(Object? data) {
  if (data is Map) {
    final detail = data['detail'];
    if (detail is String && detail.trim().isNotEmpty) {
      return detail.trim();
    }
    if (detail is List && detail.isNotEmpty) {
      return detail.map((item) => item.toString()).join('\n');
    }
  }

  return null;
}

String _fallbackMessageFor(DioException error) {
  return switch (error.type) {
    DioExceptionType.connectionTimeout ||
    DioExceptionType.sendTimeout ||
    DioExceptionType.receiveTimeout =>
      '서버 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요.',
    DioExceptionType.connectionError => '서버에 연결하지 못했어요. 네트워크 상태를 확인해 주세요.',
    _ => '요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.',
  };
}
