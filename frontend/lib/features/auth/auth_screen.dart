import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../core/mock_auth.dart';
import '../../core/repositories/auth_repository.dart';
import '../../shared/widgets/mascot_avatar.dart';

class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  var _isSignUp = false;
  var _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final name = _nameController.text.trim();
    final confirmPassword = _confirmPasswordController.text;

    if (email.isEmpty || password.isEmpty || (_isSignUp && name.isEmpty)) {
      _showSnackBar('필수 정보를 입력해 주세요.');
      return;
    }

    if (_isSignUp && password != confirmPassword) {
      _showSnackBar('비밀번호가 서로 달라요.');
      return;
    }

    final profile = _isSignUp
        ? await ref.read(authRepositoryProvider).signUp(
              nickname: name,
              email: email,
              password: password,
            )
        : await ref.read(authRepositoryProvider).signIn(
              email: email,
              password: password,
            );

    if (!mounted) return;

    ref.read(mockAuthProvider.notifier).signIn(
          email: profile.email,
          displayName: profile.displayName,
        );
    _showSnackBar(_isSignUp ? '회원가입이 완료됐어요.' : '로그인했어요.');
    context.go('/mypage');
  }

  void _continueWithoutSignIn() {
    context.go('/mypage');
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
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
                    constraints.maxWidth > 430 ? 430.0 : constraints.maxWidth;

                return Align(
                  alignment: Alignment.topCenter,
                  child: SizedBox(
                    width: contentWidth,
                    height: constraints.maxHeight,
                    child: ListView(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                      children: [
                        Align(
                          alignment: Alignment.centerLeft,
                          child: IconButton(
                            onPressed: () => context.go('/mypage'),
                            icon: const Icon(Icons.arrow_back_rounded),
                            color: ChiwawaColors.textPrimary,
                            tooltip: '뒤로가기',
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Center(child: MascotAvatar(size: 82, padding: 4)),
                        const SizedBox(height: 14),
                        const Text(
                          'chiwawa',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: ChiwawaColors.primary,
                            fontSize: 30,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          '여행 준비를 이어서 관리해요.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: ChiwawaColors.textSecondary,
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 22),
                        Container(
                          padding: const EdgeInsets.all(18),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.96),
                            borderRadius: BorderRadius.circular(24),
                            border: Border.all(color: ChiwawaColors.border),
                            boxShadow: const [
                              BoxShadow(
                                color: Color(0x12E45F78),
                                blurRadius: 24,
                                offset: Offset(0, 12),
                              ),
                            ],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              SegmentedButton<bool>(
                                segments: const [
                                  ButtonSegment(
                                    value: false,
                                    label: Text('로그인'),
                                    icon: Icon(Icons.login_rounded),
                                  ),
                                  ButtonSegment(
                                    value: true,
                                    label: Text('회원가입'),
                                    icon: Icon(Icons.person_add_alt_rounded),
                                  ),
                                ],
                                selected: {_isSignUp},
                                onSelectionChanged: (selection) {
                                  setState(() => _isSignUp = selection.first);
                                },
                              ),
                              const SizedBox(height: 18),
                              if (_isSignUp) ...[
                                _AuthTextField(
                                  key: const ValueKey('auth-name-field'),
                                  controller: _nameController,
                                  label: '닉네임',
                                  icon: Icons.badge_rounded,
                                  textInputAction: TextInputAction.next,
                                ),
                                const SizedBox(height: 12),
                              ],
                              _AuthTextField(
                                key: const ValueKey('auth-email-field'),
                                controller: _emailController,
                                label: '이메일',
                                icon: Icons.mail_rounded,
                                keyboardType: TextInputType.emailAddress,
                                textInputAction: TextInputAction.next,
                              ),
                              const SizedBox(height: 12),
                              _AuthTextField(
                                key: const ValueKey('auth-password-field'),
                                controller: _passwordController,
                                label: '비밀번호',
                                icon: Icons.lock_rounded,
                                obscureText: _obscurePassword,
                                textInputAction: _isSignUp
                                    ? TextInputAction.next
                                    : TextInputAction.done,
                                onSubmitted: (_) {
                                  if (!_isSignUp) _submit();
                                },
                                suffixIcon: IconButton(
                                  onPressed: () {
                                    setState(() {
                                      _obscurePassword = !_obscurePassword;
                                    });
                                  },
                                  icon: Icon(
                                    _obscurePassword
                                        ? Icons.visibility_rounded
                                        : Icons.visibility_off_rounded,
                                  ),
                                ),
                              ),
                              if (_isSignUp) ...[
                                const SizedBox(height: 12),
                                _AuthTextField(
                                  key: const ValueKey(
                                    'auth-confirm-password-field',
                                  ),
                                  controller: _confirmPasswordController,
                                  label: '비밀번호 확인',
                                  icon: Icons.verified_user_rounded,
                                  obscureText: _obscurePassword,
                                  textInputAction: TextInputAction.done,
                                  onSubmitted: (_) => _submit(),
                                ),
                              ],
                              const SizedBox(height: 18),
                              FilledButton.icon(
                                key: const ValueKey('auth-submit-button'),
                                onPressed: _submit,
                                icon: Icon(
                                  _isSignUp
                                      ? Icons.person_add_alt_rounded
                                      : Icons.login_rounded,
                                  size: 18,
                                ),
                                label: Text(_isSignUp ? '회원가입' : '로그인'),
                              ),
                              const SizedBox(height: 10),
                              TextButton(
                                onPressed: _continueWithoutSignIn,
                                child: const Text('로그인 없이 둘러보기'),
                              ),
                            ],
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

class _AuthTextField extends StatelessWidget {
  const _AuthTextField({
    super.key,
    required this.controller,
    required this.label,
    required this.icon,
    this.keyboardType,
    this.textInputAction,
    this.obscureText = false,
    this.suffixIcon,
    this.onSubmitted,
  });

  final TextEditingController controller;
  final String label;
  final IconData icon;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final bool obscureText;
  final Widget? suffixIcon;
  final ValueChanged<String>? onSubmitted;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      textInputAction: textInputAction,
      obscureText: obscureText,
      onSubmitted: onSubmitted,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        suffixIcon: suffixIcon,
        filled: true,
        fillColor: ChiwawaColors.background,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}
