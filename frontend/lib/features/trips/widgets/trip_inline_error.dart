import 'package:flutter/material.dart';

import '../../../app/theme.dart';

class TripInlineError extends StatelessWidget {
  const TripInlineError({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF1F4),
        border: Border.all(color: ChiwawaColors.border),
        borderRadius: BorderRadius.circular(ChiwawaRadii.control),
      ),
      child: Text(
        message,
        style: const TextStyle(
          color: ChiwawaColors.primary,
          fontSize: 13,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
