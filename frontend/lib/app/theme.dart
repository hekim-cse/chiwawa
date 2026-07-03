import 'package:flutter/material.dart';

class ChiwawaColors {
  static const primary = Color(0xFFE45F78);
  static const secondary = Color(0xFFFFEEF2);
  static const background = Color(0xFFFFF9FA);
  static const card = Colors.white;
  static const textPrimary = Color(0xFF22191C);
  static const textSecondary = Color(0xFF7C7074);
  static const textMuted = Color(0xFFC7B9BD);
  static const border = Color(0xFFF3DFE5);
}

class ChiwawaTheme {
  static ThemeData light() {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: ChiwawaColors.primary,
        primary: ChiwawaColors.primary,
        secondary: ChiwawaColors.secondary,
        surface: ChiwawaColors.card,
      ),
      fontFamily: 'Pretendard',
      scaffoldBackgroundColor: ChiwawaColors.background,
    );

    return base.copyWith(
      appBarTheme: const AppBarTheme(
        elevation: 0,
        backgroundColor: ChiwawaColors.background,
        foregroundColor: ChiwawaColors.textPrimary,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        color: ChiwawaColors.card,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          side: const BorderSide(color: ChiwawaColors.border),
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      chipTheme: base.chipTheme.copyWith(
        side: const BorderSide(color: ChiwawaColors.border),
        selectedColor: ChiwawaColors.primary,
        backgroundColor: Colors.white,
        labelStyle: const TextStyle(
          color: ChiwawaColors.textSecondary,
          fontWeight: FontWeight.w600,
        ),
      ),
      textTheme: base.textTheme.apply(
        bodyColor: ChiwawaColors.textPrimary,
        displayColor: ChiwawaColors.textPrimary,
      ),
      dividerTheme: const DividerThemeData(
        color: ChiwawaColors.border,
        thickness: 1,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          elevation: 0,
          foregroundColor: Colors.white,
          backgroundColor: ChiwawaColors.primary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: ChiwawaColors.primary,
          side: const BorderSide(color: ChiwawaColors.primary),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}
