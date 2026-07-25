import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../app/theme.dart';
import '../../../core/env.dart';
import '../widgets/my_page_detail_scaffold.dart';

class SupportScreen extends StatefulWidget {
  const SupportScreen({super.key});

  @override
  State<SupportScreen> createState() => _SupportScreenState();
}

class _SupportScreenState extends State<SupportScreen> {
  final _formKey = GlobalKey<FormState>();
  final _messageController = TextEditingController();
  String _category = '앱 이용';
  var _includeDiagnostics = true;

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MyPageDetailScaffold(
      title: '문의하기',
      subtitle: '문의 내용을 작성하면 기본 이메일 앱으로 연결해요.',
      bottomAction: FilledButton.icon(
        key: const ValueKey('submit-support-inquiry'),
        onPressed: _submit,
        icon: const Icon(Icons.send_rounded),
        label: const Text('이메일로 문의'),
      ),
      children: [
        const MyPageStatusBanner(
          icon: Icons.mail_outline_rounded,
          title: 'support@chiwawa.app',
          description: '이메일 앱을 열 수 없는 환경에서는 문의 주소와 내용을 복사해요.',
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageSection(
          title: '문의 전 확인',
          child: Column(
            children: [
              MyPageDetailItem(
                icon: Icons.screenshot_outlined,
                title: '확인한 화면',
                description: '홈, 일정, 탐색처럼 문제가 발생한 화면을 적어 주세요.',
              ),
              MyPageDetailItem(
                icon: Icons.replay_rounded,
                title: '다시 발생하는 순서',
                description: '어떤 버튼을 눌렀는지 순서대로 적으면 확인이 빨라져요.',
              ),
              MyPageDetailItem(
                icon: Icons.lock_outline_rounded,
                title: '민감한 정보 제외',
                description: '비밀번호, 인증 코드, 전체 위치 좌표는 적지 마세요.',
                showDivider: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DropdownButtonFormField<String>(
                key: const ValueKey('support-category-field'),
                initialValue: _category,
                decoration: const InputDecoration(
                  labelText: '문의 유형',
                  prefixIcon: Icon(Icons.category_outlined),
                ),
                items: const [
                  DropdownMenuItem(value: '앱 이용', child: Text('앱 이용')),
                  DropdownMenuItem(value: '여행 데이터', child: Text('여행 데이터')),
                  DropdownMenuItem(value: '사진과 위치', child: Text('사진과 위치')),
                  DropdownMenuItem(value: '계정', child: Text('계정')),
                  DropdownMenuItem(value: '오류 제보', child: Text('오류 제보')),
                ],
                onChanged: (value) {
                  if (value != null) setState(() => _category = value);
                },
              ),
              const SizedBox(height: ChiwawaSpacing.md),
              TextFormField(
                key: const ValueKey('support-message-field'),
                controller: _messageController,
                minLines: 6,
                maxLines: 9,
                maxLength: 1000,
                decoration: const InputDecoration(
                  labelText: '문의 내용',
                  alignLabelWithHint: true,
                  hintText: '확인한 화면과 상황을 함께 적어 주세요.',
                ),
                validator: (value) {
                  if (value == null || value.trim().length < 10) {
                    return '문의 내용을 10자 이상 입력해 주세요.';
                  }
                  return null;
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        MyPageSection(
          title: '자동 첨부 정보',
          padding: EdgeInsets.zero,
          surface: true,
          child: Column(
            children: [
              SwitchListTile(
                key: const ValueKey('support-diagnostics-switch'),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14),
                title: const Text('앱 진단 정보 포함'),
                subtitle: const Text('버전, 실행 환경, 데이터 모드만 포함해요.'),
                value: _includeDiagnostics,
                onChanged: (value) {
                  setState(() => _includeDiagnostics = value);
                },
              ),
              if (_includeDiagnostics) ...[
                const Divider(height: 1, indent: 14, endIndent: 14),
                Padding(
                  padding: const EdgeInsets.all(ChiwawaSpacing.sm),
                  child: Text(
                    _diagnostics,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: ChiwawaColors.textSecondary,
                        ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  String get _diagnostics => [
        '앱 버전: 1.0.0',
        '빌드 SHA: $appBuildSha',
        '실행 환경: ${kIsWeb ? 'Web' : 'App'}',
        '데이터 모드: ${useApiBackend ? 'API' : 'Mock'}',
      ].join('\n');

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final message = _messageController.text.trim();
    final subject = '[chiwawa $_category 문의]';
    final body = [
      message,
      if (_includeDiagnostics) '\n--- 앱 진단 정보 ---\n$_diagnostics',
    ].join('\n');
    final uri = Uri(
      scheme: 'mailto',
      path: 'support@chiwawa.app',
      queryParameters: {
        'subject': subject,
        'body': body,
      },
    );

    try {
      final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (opened || !mounted) return;
    } catch (_) {
      if (!mounted) return;
    }

    await Clipboard.setData(
      ClipboardData(
        text: 'support@chiwawa.app\n$subject\n\n$body',
      ),
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('문의 주소와 내용을 복사했어요.')),
    );
  }
}
