import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/router.dart';
import 'app/theme.dart';

void main() {
  runApp(const ProviderScope(child: ChiwawaApp()));
}

class ChiwawaApp extends ConsumerWidget {
  const ChiwawaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'chiwawa',
      debugShowCheckedModeBanner: false,
      theme: ChiwawaTheme.light(),
      routerConfig: router,
    );
  }
}
