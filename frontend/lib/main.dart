import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/router.dart';
import 'app/theme.dart';
import 'core/auth/deep_link_service.dart';
import 'core/auth/auth_session_validator.dart';

void main() {
  runApp(const ProviderScope(child: ChiwawaApp()));
}

class ChiwawaApp extends ConsumerStatefulWidget {
  const ChiwawaApp({super.key});

  @override
  ConsumerState<ChiwawaApp> createState() => _ChiwawaAppState();
}

class _ChiwawaAppState extends ConsumerState<ChiwawaApp> {
  @override
  void initState() {
    super.initState();
    // 구글 로그인 앱 복귀(chiwawa://auth?code=...) 수신 시작
    unawaited(ref.read(deepLinkServiceProvider).start());
    unawaited(ref.read(authSessionValidatorProvider).validateRestoredSession());
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'chiwawa',
      debugShowCheckedModeBanner: false,
      theme: ChiwawaTheme.light(),
      routerConfig: router,
    );
  }
}
