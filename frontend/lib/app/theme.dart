import 'package:flutter/material.dart';

class ChiwawaColors {
  static const primary = Color(0xFFE45F78);
  static const primaryPressed = Color(0xFFC94863);
  static const secondary = Color(0xFFFFEEF2);
  static const background = Color(0xFFFCFBFC);
  static const card = Colors.white;
  static const textPrimary = Color(0xFF5A2F3B);
  static const textSecondary = Color(0xFF7C7074);
  static const textMuted = Color(0xFFC7B9BD);
  static const border = Color(0xFFECE8EA);
  static const surfaceMuted = Color(0xFFF7F5F6);
  static const success = Color(0xFF2F7D5B);
  static const movement = Color(0xFF4D7773);
  static const movementSurface = Color(0xFFEAF4F2);
  static const warning = Color(0xFFA46525);
  static const warningSurface = Color(0xFFFFF4E6);
  static const mapWater = Color(0xFFEAF4F7);
  static const mapLand = Color(0xFFF6F4EE);
}

abstract final class ChiwawaSpacing {
  static const xxs = 4.0;
  static const xs = 8.0;
  static const sm = 12.0;
  static const md = 16.0;
  static const lg = 20.0;
  static const xl = 24.0;
  static const section = 28.0;
  static const pageTop = 20.0;
}

abstract final class ChiwawaRadii {
  static const control = 10.0;
  static const card = 12.0;
  static const sheet = 20.0;
  static const round = 999.0;
}

abstract final class ChiwawaControlSizes {
  static const minimumInteractive = 48.0;
  static const navigationBar = 66.0;
}

class ChiwawaTheme {
  static Color? primaryStateLayer(Set<WidgetState> states) {
    if (states.contains(WidgetState.pressed)) {
      return ChiwawaColors.primary.withValues(alpha: 0.12);
    }
    if (states.contains(WidgetState.hovered) ||
        states.contains(WidgetState.focused)) {
      return ChiwawaColors.primary.withValues(alpha: 0.08);
    }
    return null;
  }

  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: ChiwawaColors.primary,
      primary: ChiwawaColors.primary,
      secondary: ChiwawaColors.secondary,
      surface: ChiwawaColors.card,
    ).copyWith(
      onSurface: ChiwawaColors.textPrimary,
      onSurfaceVariant: ChiwawaColors.textSecondary,
    );
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      fontFamily: 'Pretendard',
      scaffoldBackgroundColor: ChiwawaColors.background,
      hoverColor: ChiwawaColors.primary.withValues(alpha: 0.06),
      focusColor: ChiwawaColors.primary.withValues(alpha: 0.08),
      highlightColor: ChiwawaColors.primary.withValues(alpha: 0.10),
      splashColor: ChiwawaColors.primary.withValues(alpha: 0.08),
    );

    final textTheme = base.textTheme
        .copyWith(
          headlineSmall: const TextStyle(
            fontSize: 24,
            height: 1.2,
            fontWeight: FontWeight.w800,
            letterSpacing: 0,
          ),
          titleLarge: const TextStyle(
            fontSize: 21,
            height: 1.25,
            fontWeight: FontWeight.w800,
            letterSpacing: 0,
          ),
          titleMedium: const TextStyle(
            fontSize: 17,
            height: 1.3,
            fontWeight: FontWeight.w700,
            letterSpacing: 0,
          ),
          titleSmall: const TextStyle(
            fontSize: 15,
            height: 1.35,
            fontWeight: FontWeight.w700,
            letterSpacing: 0,
          ),
          bodyLarge: const TextStyle(
            fontSize: 15,
            height: 1.5,
            fontWeight: FontWeight.w500,
            letterSpacing: 0,
          ),
          bodyMedium: const TextStyle(
            fontSize: 14,
            height: 1.45,
            fontWeight: FontWeight.w500,
            letterSpacing: 0,
          ),
          bodySmall: const TextStyle(
            fontSize: 12,
            height: 1.4,
            fontWeight: FontWeight.w500,
            letterSpacing: 0,
          ),
          labelLarge: const TextStyle(
            fontSize: 14,
            height: 1.25,
            fontWeight: FontWeight.w700,
            letterSpacing: 0,
          ),
          labelMedium: const TextStyle(
            fontSize: 12,
            height: 1.25,
            fontWeight: FontWeight.w600,
            letterSpacing: 0,
          ),
        )
        .apply(
          bodyColor: ChiwawaColors.textPrimary,
          displayColor: ChiwawaColors.textPrimary,
        );

    return base.copyWith(
      textTheme: textTheme,
      appBarTheme: const AppBarTheme(
        elevation: 0,
        backgroundColor: ChiwawaColors.background,
        foregroundColor: ChiwawaColors.textPrimary,
        centerTitle: false,
      ),
      iconButtonTheme: IconButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size.square(ChiwawaControlSizes.minimumInteractive),
          ),
          foregroundColor: const WidgetStatePropertyAll(
            ChiwawaColors.textPrimary,
          ),
          overlayColor: WidgetStateProperty.resolveWith(primaryStateLayer),
        ),
      ),
      cardTheme: CardThemeData(
        color: ChiwawaColors.card,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: ChiwawaColors.border),
          borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        ),
      ),
      chipTheme: base.chipTheme.copyWith(
        side: const BorderSide(color: ChiwawaColors.border),
        selectedColor: ChiwawaColors.primary,
        checkmarkColor: Colors.white,
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(ChiwawaRadii.control),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        labelStyle: const TextStyle(
          color: ChiwawaColors.textSecondary,
          fontSize: 13,
          height: 1.2,
          fontWeight: FontWeight.w700,
        ),
        secondaryLabelStyle: const TextStyle(
          color: Colors.white,
          fontSize: 13,
          height: 1.2,
          fontWeight: FontWeight.w800,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 15,
        ),
        labelStyle: const TextStyle(
          color: ChiwawaColors.textSecondary,
          fontSize: 13,
          fontWeight: FontWeight.w700,
        ),
        hintStyle: const TextStyle(
          color: ChiwawaColors.textMuted,
          fontSize: 14,
          fontWeight: FontWeight.w500,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(ChiwawaRadii.control),
          borderSide: const BorderSide(color: ChiwawaColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(ChiwawaRadii.control),
          borderSide: const BorderSide(color: ChiwawaColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(ChiwawaRadii.control),
          borderSide: const BorderSide(
            color: ChiwawaColors.primary,
            width: 1.4,
          ),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: ChiwawaColors.border,
        thickness: 1,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size(
            ChiwawaControlSizes.minimumInteractive,
            ChiwawaControlSizes.minimumInteractive,
          ),
          elevation: 0,
          foregroundColor: Colors.white,
          backgroundColor: ChiwawaColors.primary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(ChiwawaRadii.control),
          ),
          textStyle: textTheme.labelLarge,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size(
              ChiwawaControlSizes.minimumInteractive,
              ChiwawaControlSizes.minimumInteractive,
            ),
          ),
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.pressed)) {
              return ChiwawaColors.primaryPressed;
            }
            return ChiwawaColors.primary;
          }),
          foregroundColor: const WidgetStatePropertyAll(Colors.white),
          overlayColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.pressed)) {
              return Colors.white.withValues(alpha: 0.16);
            }
            if (states.contains(WidgetState.hovered) ||
                states.contains(WidgetState.focused)) {
              return Colors.white.withValues(alpha: 0.10);
            }
            return null;
          }),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(ChiwawaRadii.control),
            ),
          ),
          textStyle: WidgetStatePropertyAll(textTheme.labelLarge),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size(
              ChiwawaControlSizes.minimumInteractive,
              ChiwawaControlSizes.minimumInteractive,
            ),
          ),
          foregroundColor: const WidgetStatePropertyAll(
            ChiwawaColors.primary,
          ),
          side: const WidgetStatePropertyAll(
            BorderSide(color: ChiwawaColors.border),
          ),
          overlayColor: WidgetStateProperty.resolveWith(primaryStateLayer),
          shape: WidgetStatePropertyAll(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(ChiwawaRadii.control),
            ),
          ),
          textStyle: WidgetStatePropertyAll(textTheme.labelLarge),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: ButtonStyle(
          minimumSize: const WidgetStatePropertyAll(
            Size(
              ChiwawaControlSizes.minimumInteractive,
              ChiwawaControlSizes.minimumInteractive,
            ),
          ),
          foregroundColor: const WidgetStatePropertyAll(
            ChiwawaColors.primary,
          ),
          overlayColor: WidgetStateProperty.resolveWith(primaryStateLayer),
          textStyle: WidgetStatePropertyAll(textTheme.labelLarge),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          return states.contains(WidgetState.selected)
              ? Colors.white
              : ChiwawaColors.textMuted;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          return states.contains(WidgetState.selected)
              ? ChiwawaColors.primary
              : ChiwawaColors.border;
        }),
        trackOutlineColor: WidgetStateProperty.resolveWith((states) {
          return states.contains(WidgetState.selected)
              ? Colors.transparent
              : ChiwawaColors.textMuted;
        }),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: ChiwawaControlSizes.navigationBar,
        labelTextStyle: WidgetStatePropertyAll(textTheme.labelMedium),
        iconTheme: const WidgetStatePropertyAll(IconThemeData(size: 22)),
      ),
      snackBarTheme: const SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: ChiwawaColors.textPrimary,
        contentTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 13,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
