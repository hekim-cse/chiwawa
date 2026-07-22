import 'package:flutter/material.dart';

class MyPageMenuItem {
  const MyPageMenuItem({
    required this.title,
    required this.description,
    required this.icon,
    required this.route,
    this.value,
  });

  final String title;
  final String description;
  final IconData icon;
  final String route;
  final String? value;
}
