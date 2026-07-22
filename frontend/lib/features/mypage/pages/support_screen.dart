import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../app/theme.dart';
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
      ],
    );
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final message = _messageController.text.trim();
    final subject = '[chiwawa $_category 문의]';
    final uri = Uri(
      scheme: 'mailto',
      path: 'support@chiwawa.app',
      queryParameters: {
        'subject': subject,
        'body': message,
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
        text: 'support@chiwawa.app\n$subject\n\n$message',
      ),
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('문의 주소와 내용을 복사했어요.')),
    );
  }
}
