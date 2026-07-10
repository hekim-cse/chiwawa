import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/theme.dart';
import '../../shared/widgets/app_viewport.dart';
import '../../core/api/dio_client.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/env.dart';
import '../../core/repositories/auth_repository.dart';
import '../../shared/widgets/mascot_avatar.dart';

/// 첫 진입 로그인 화면 — 구글 로그인 + 로그인 없이 둘러보기
class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({
    this.oauthCode,
    this.oauthState,
    super.key,
  });

  final String? oauthCode;
  final String? oauthState;

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  var _launching = false;
  var _handledInitialCode = false;

  @override
  void initState() {
    super.initState();
    if (widget.oauthCode != null && widget.oauthCode!.isNotEmpty) {
      _handledInitialCode = true;
      unawaited(Future<void>.microtask(_exchangeOAuthCode));
    }
  }

  @override
  void didUpdateWidget(covariant AuthScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_handledInitialCode &&
        widget.oauthCode != null &&
        widget.oauthCode!.isNotEmpty &&
        widget.oauthCode != oldWidget.oauthCode) {
      _handledInitialCode = true;
      unawaited(_exchangeOAuthCode());
    }
  }

  Future<void> _signInWithGoogle() async {
    if (_launching) return;
    setState(() => _launching = true);

    try {
      if (useApiBackend) {
        // 실서버: 백엔드가 구글 동의 화면으로 리다이렉트 →
        // 로그인 완료 시 chiwawa://auth?code=... 로 앱 복귀하면
        // DeepLinkService가 callback API로 access_token을 교환한다.
        final baseUrl = ref.read(apiBaseUrlProvider);
        final loginUri = Uri.parse('$baseUrl/api/v1/auth/google/login');
        final opened = await launchUrl(
          loginUri,
          mode: LaunchMode.externalApplication,
        );
        if (!opened && mounted) {
          _showSnackBar('브라우저를 열지 못했어요. 잠시 후 다시 시도해 주세요.');
        }
      } else {
        // Mock: 백엔드 없이 로그인 성공 플로우 재현
        // 영속화(unawaited)는 뒤에서 진행 — 화면 이동을 저장 완료에 묶지 않는다
        unawaited(
          ref.read(authControllerProvider.notifier).signInWithToken(
                'mock-jwt-token',
                user: const AuthUser(
                  name: '치와와 여행자',
                  email: 'traveler@chiwawa.app',
                ),
              ),
        );
        if (mounted) context.go('/home');
      }
    } finally {
      if (mounted) setState(() => _launching = false);
    }
  }

  Future<void> _exchangeOAuthCode() async {
    final code = widget.oauthCode;
    if (code == null || code.isEmpty || _launching) return;

    setState(() => _launching = true);
    try {
      final result =
          await ref.read(authRepositoryProvider).signInWithGoogleCode(
                code,
                state: widget.oauthState,
              );
      await ref.read(authControllerProvider.notifier).signInWithToken(
            result.accessToken,
            user: AuthUser(
              name: result.profile.displayName,
              email: result.profile.email,
              pictureUrl: result.pictureUrl,
            ),
          );
      if (mounted) context.go('/home');
    } catch (_) {
      if (mounted) {
        _showSnackBar('구글 로그인에 실패했어요. 다시 시도해 주세요.');
      }
    } finally {
      if (mounted) setState(() => _launching = false);
    }
  }

  void _continueAsGuest() {
    // 상태 변경은 동기, 영속화는 백그라운드 — 이동이 저장에 막히지 않게 한다
    unawaited(ref.read(authControllerProvider.notifier).continueAsGuest());
    context.go('/home');
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);

    return Scaffold(
      body: SafeArea(
        child: SizedBox.expand(
          child: DecoratedBox(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFFFFF6F8),
                  Color(0xFFFFFBFC),
                  ChiwawaColors.background,
                ],
              ),
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final contentWidth =
                    constraints.maxWidth > AppLayout.maxContentWidth
                        ? AppLayout.maxContentWidth
                        : constraints.maxWidth;

                return Align(
                  alignment: Alignment.topCenter,
                  child: SizedBox(
                    width: contentWidth,
                    height: constraints.maxHeight,
                    child: ListView(
                      padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
                      children: [
                        if (auth.isGuest)
                          Align(
                            alignment: Alignment.centerLeft,
                            child: IconButton(
                              onPressed: () => context.go('/mypage'),
                              icon: const Icon(Icons.arrow_back_rounded),
                              color: ChiwawaColors.textPrimary,
                              tooltip: '뒤로가기',
                            ),
                          )
                        else
                          const SizedBox(height: 48),
                        const SizedBox(height: 36),
                        const Center(
                          child: MascotAvatar(size: 96, padding: 5),
                        ),
                        const SizedBox(height: 18),
                        const Text(
                          '치와와',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: ChiwawaColors.primary,
                            fontSize: 32,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'AI와 함께하는 일본 여행 플래너',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: ChiwawaColors.textSecondary,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 52),
                        _GoogleSignInButton(
                          launching: _launching,
                          onPressed: _signInWithGoogle,
                        ),
                        const SizedBox(height: 14),
                        TextButton(
                          onPressed: _continueAsGuest,
                          style: TextButton.styleFrom(
                            foregroundColor: ChiwawaColors.textSecondary,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                          child: const Text(
                            '로그인 없이 둘러보기',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                              decoration: TextDecoration.underline,
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),
                        const Text(
                          '로그인하면 여행 일정이 계정에 안전하게 보관돼요',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: ChiwawaColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ),
      ),
    );
  }
}

class _GoogleSignInButton extends StatelessWidget {
  const _GoogleSignInButton({
    required this.launching,
    required this.onPressed,
  });

  final bool launching;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 54,
      child: OutlinedButton(
        onPressed: launching ? null : onPressed,
        style: OutlinedButton.styleFrom(
          backgroundColor: Colors.white,
          side: const BorderSide(color: ChiwawaColors.border),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        child: launching
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: ChiwawaColors.primary,
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 26,
                    height: 26,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                      border: Border.all(color: ChiwawaColors.border),
                    ),
                    child: const Text(
                      'G',
                      style: TextStyle(
                        color: Color(0xFF4285F4),
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    'Google로 시작하기',
                    style: TextStyle(
                      color: ChiwawaColors.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
