import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../shared/widgets/app_viewport.dart';
import '../my_page_routes.dart';

class MyPageDetailScaffold extends StatelessWidget {
  const MyPageDetailScaffold({
    required this.title,
    required this.subtitle,
    required this.children,
    this.bottomAction,
    super.key,
  });

  final String title;
  final String subtitle;
  final List<Widget> children;
  final Widget? bottomAction;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ColoredBox(
        color: ChiwawaColors.background,
        child: Column(
          children: [
            _DetailHeader(
              title: title,
              onBack: () {
                if (context.canPop()) {
                  context.pop();
                } else {
                  context.go(MyPageRoutes.overview);
                }
              },
            ),
            Expanded(
              child: ListView(
                padding: AppLayout.pageInsets(
                  context,
                  top: ChiwawaSpacing.sm,
                  bottom: bottomAction == null ? 32 : 20,
                ),
                children: [
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: ChiwawaColors.textSecondary,
                        ),
                  ),
                  const SizedBox(height: ChiwawaSpacing.lg),
                  ...children,
                ],
              ),
            ),
            if (bottomAction != null)
              Container(
                width: double.infinity,
                padding: AppLayout.pageInsets(
                  context,
                  top: ChiwawaSpacing.sm,
                  bottom: ChiwawaSpacing.sm,
                ),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  border: Border(
                    top: BorderSide(color: ChiwawaColors.border),
                  ),
                ),
                child: bottomAction,
              ),
          ],
        ),
      ),
    );
  }
}

class _DetailHeader extends StatelessWidget {
  const _DetailHeader({required this.title, required this.onBack});

  final String title;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 58,
      padding: EdgeInsets.symmetric(
        horizontal: AppLayout.pageHorizontalPadding(context),
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: ChiwawaColors.border)),
      ),
      child: Row(
        children: [
          IconButton(
            tooltip: '마이페이지로 돌아가기',
            onPressed: onBack,
            icon: const Icon(Icons.arrow_back_rounded),
          ),
          const SizedBox(width: ChiwawaSpacing.xs),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class MyPageSection extends StatelessWidget {
  const MyPageSection({
    required this.child,
    this.title,
    this.padding = const EdgeInsets.all(ChiwawaSpacing.md),
    super.key,
  });

  final String? title;
  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (title != null) ...[
          Text(title!, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: ChiwawaSpacing.xs),
        ],
        Material(
          color: Colors.white,
          clipBehavior: Clip.antiAlias,
          shape: RoundedRectangleBorder(
            side: const BorderSide(color: ChiwawaColors.border),
            borderRadius: BorderRadius.circular(ChiwawaRadii.card),
          ),
          child: Padding(padding: padding, child: child),
        ),
      ],
    );
  }
}

class MyPageInfoRow extends StatelessWidget {
  const MyPageInfoRow({
    required this.label,
    required this.value,
    this.showDivider = true,
    super.key,
  });

  final String label;
  final String value;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    final stackValues = MediaQuery.sizeOf(context).width <= 340 ||
        MediaQuery.textScalerOf(context).scale(1) >= 1.25;
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: ChiwawaSpacing.sm),
          child: stackValues
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: ChiwawaColors.textSecondary,
                          ),
                    ),
                    const SizedBox(height: ChiwawaSpacing.xxs),
                    Text(
                      value,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                  ],
                )
              : Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 92,
                      child: Text(
                        label,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: ChiwawaColors.textSecondary,
                            ),
                      ),
                    ),
                    const SizedBox(width: ChiwawaSpacing.sm),
                    Expanded(
                      child: Text(
                        value,
                        textAlign: TextAlign.right,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                    ),
                  ],
                ),
        ),
        if (showDivider) const Divider(height: 1),
      ],
    );
  }
}

class MyPageStatusBanner extends StatelessWidget {
  const MyPageStatusBanner({
    required this.icon,
    required this.title,
    required this.description,
    this.color = ChiwawaColors.primary,
    super.key,
  });

  final IconData icon;
  final String title;
  final String description;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(ChiwawaSpacing.md),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: ChiwawaSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: color,
                      ),
                ),
                const SizedBox(height: ChiwawaSpacing.xxs),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: ChiwawaColors.textSecondary,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
