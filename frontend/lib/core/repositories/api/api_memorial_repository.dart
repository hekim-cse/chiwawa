import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../api/api_exception.dart';
import '../../models/memorial_models.dart';
import '../memorial_repository.dart';

class ApiMemorialRepository implements MemorialRepository {
  const ApiMemorialRepository({required this.dio});

  final Dio dio;

  @override
  Future<MemorialOverview?> fetchOverview() async => null;

  @override
  Future<MemorialCalendar> fetchCalendar(MemorialMonth month) async {
    final json = await _getJson(
      '/api/v1/memorial/calendar',
      queryParameters: {'year': month.year, 'month': month.month},
    );
    return MemorialCalendar.fromJson(json);
  }

  @override
  Future<MemorialDayTimeline> fetchDay(DateTime day) async {
    final json = await _getJson('/api/v1/memorial/days/${_formatDate(day)}');
    return MemorialDayTimeline.fromJson(json);
  }

  @override
  Future<Uint8List> fetchPhotoBytes(String fileUrl) async {
    try {
      final response = await dio.get<List<int>>(
        fileUrl,
        options: Options(responseType: ResponseType.bytes),
      );
      return Uint8List.fromList(response.data ?? const []);
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  Future<Map<String, Object?>> _getJson(
    String path, {
    Map<String, Object?>? queryParameters,
  }) async {
    try {
      final response = await dio.get<Map<String, Object?>>(
        path,
        queryParameters: queryParameters,
      );
      return response.data ?? const {};
    } on DioException catch (error) {
      throw ApiException.fromDioException(error);
    }
  }

  String _formatDate(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}-$month-$day';
  }
}
