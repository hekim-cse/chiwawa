import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import 'app_status_view.dart';

/// AsyncValue의 loading/error/data 3분기를 공통 처리하는 뷰.
/// 에러 시 빈 화면 대신 메시지와 재시도 버튼을 보여준다.
class AsyncValueView<T> extends StatelessWidget {
  const AsyncValueView({
    required this.value,
    required this.builder,
    this.onRetry,
    this.loadingHeight = 180,
    super.key,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final VoidCallback? onRetry;
  final double loadingHeight;

  @override
  Widget build(BuildContext context) {
    return value.when(
      data: builder,
      loading: () => AppLoadingView(height: loadingHeight),
      error: (error, _) => AppStatusView(
        kind: AppStatusKind.error,
        title: '내용을 불러오지 못했어요',
        message: mapApiErrorToMessage(error),
        actionLabel: onRetry == null ? null : '다시 시도',
        onAction: onRetry,
        compact: true,
      ),
    );
  }
}
