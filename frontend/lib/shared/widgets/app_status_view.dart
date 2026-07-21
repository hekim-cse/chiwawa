import 'package:flutter/material.dart';

import '../../app/theme.dart';
import 'mascot_avatar.dart';

enum AppStatusKind { empty, error }

class AppStatusView extends StatelessWidget {
  const AppStatusView({
    required this.kind,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.compact = false,
    super.key,
  });

  final AppStatusKind kind;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final icon = kind == AppStatusKind.error
        ? const Icon(
            Icons.error_outline_rounded,
            color: ChiwawaColors.primary,
            size: 30,
          )
        : MascotAvatar(size: compact ? 44 : 58);

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: ChiwawaSpacing.lg,
        vertical: compact ? ChiwawaSpacing.lg : ChiwawaSpacing.section,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          icon,
          const SizedBox(height: ChiwawaSpacing.sm),
          Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: ChiwawaSpacing.xs),
          Text(
            message,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: ChiwawaColors.textSecondary,
                ),
          ),
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: ChiwawaSpacing.md),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    );
  }
}

class AppLoadingView extends StatelessWidget {
  const AppLoadingView({this.height = 180, super.key});

  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      child: const Center(
        child: SizedBox.square(
          dimension: 24,
          child: CircularProgressIndicator(
            strokeWidth: 2.4,
            color: ChiwawaColors.primary,
          ),
        ),
      ),
    );
  }
}
