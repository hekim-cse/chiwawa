import 'package:flutter/material.dart';

import '../../app/theme.dart';

class AppListGroup extends StatelessWidget {
  const AppListGroup({required this.children, super.key});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Column(children: children),
    );
  }
}

class AppListRow extends StatelessWidget {
  const AppListRow({
    required this.title,
    this.titleColor,
    this.subtitle,
    this.subtitleColor,
    this.leading,
    this.trailing,
    this.onTap,
    this.showDivider = true,
    this.minHeight = 68,
    super.key,
  });

  final String title;
  final Color? titleColor;
  final String? subtitle;
  final Color? subtitleColor;
  final Widget? leading;
  final Widget? trailing;
  final VoidCallback? onTap;
  final bool showDivider;
  final double minHeight;

  @override
  Widget build(BuildContext context) {
    final content = ConstrainedBox(
      constraints: BoxConstraints(minHeight: minHeight),
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          ChiwawaSpacing.md,
          ChiwawaSpacing.sm,
          onTap == null ? ChiwawaSpacing.md : ChiwawaSpacing.sm,
          ChiwawaSpacing.sm,
        ),
        child: Row(
          children: [
            if (leading != null) ...[
              leading!,
              const SizedBox(width: ChiwawaSpacing.sm),
            ],
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: titleColor,
                        ),
                  ),
                  if (subtitle != null && subtitle!.trim().isNotEmpty) ...[
                    const SizedBox(height: ChiwawaSpacing.xxs),
                    Text(
                      subtitle!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: subtitleColor ?? ChiwawaColors.textSecondary,
                          ),
                    ),
                  ],
                ],
              ),
            ),
            if (trailing != null) ...[
              const SizedBox(width: ChiwawaSpacing.sm),
              trailing!,
            ] else if (onTap != null) ...[
              const SizedBox(width: ChiwawaSpacing.xs),
              const Icon(
                Icons.chevron_right_rounded,
                color: ChiwawaColors.textMuted,
              ),
            ],
          ],
        ),
      ),
    );

    return Column(
      children: [
        if (onTap == null) content else InkWell(onTap: onTap, child: content),
        if (showDivider)
          Divider(
            height: 1,
            indent: leading == null ? 0 : 52,
          ),
      ],
    );
  }
}

class AppLeadingIcon extends StatelessWidget {
  const AppLeadingIcon({
    required this.icon,
    this.color = ChiwawaColors.textSecondary,
    super.key,
  });

  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 36,
      height: 36,
      child: Icon(icon, size: 21, color: color),
    );
  }
}
