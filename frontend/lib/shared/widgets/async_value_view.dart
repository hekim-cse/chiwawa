import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme.dart';
import '../../core/api/api_exception.dart';

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
      loading: () => SizedBox(
        height: loadingHeight,
        child: const Center(
          child: CircularProgressIndicator(color: ChiwawaColors.primary),
        ),
      ),
      error: (error, _) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: ChiwawaColors.secondary,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: ChiwawaColors.border),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline_rounded,
              color: ChiwawaColors.primary,
              size: 32,
            ),
            const SizedBox(height: 10),
            Text(
              mapApiErrorToMessage(error),
              textAlign: TextAlign.center,
              style: const TextStyle(color: ChiwawaColors.textSecondary),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 8),
              TextButton(
                onPressed: onRetry,
                child: const Text('다시 시도'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
