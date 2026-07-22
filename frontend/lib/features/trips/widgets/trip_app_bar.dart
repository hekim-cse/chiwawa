import 'package:flutter/material.dart';

class TripAppBar extends StatelessWidget {
  const TripAppBar({
    required this.onBack,
    required this.onAdd,
    super.key,
  });

  final VoidCallback onBack;
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 60,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        child: Row(
          children: [
            IconButton(
              tooltip: '마이페이지로 돌아가기',
              onPressed: onBack,
              icon: const Icon(Icons.arrow_back_rounded),
            ),
            const Expanded(
              child: Text(
                '내 여행',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900),
              ),
            ),
            IconButton(
              key: const ValueKey('open-trip-create'),
              tooltip: '새 여행 만들기',
              onPressed: onAdd,
              icon: const Icon(Icons.add_rounded),
            ),
          ],
        ),
      ),
    );
  }
}
