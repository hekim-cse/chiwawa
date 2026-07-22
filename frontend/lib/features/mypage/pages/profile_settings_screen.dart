import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/auth/auth_controller.dart';
import '../../../shared/widgets/mascot_avatar.dart';
import '../widgets/my_page_detail_scaffold.dart';

class ProfileSettingsScreen extends ConsumerStatefulWidget {
  const ProfileSettingsScreen({super.key});

  @override
  ConsumerState<ProfileSettingsScreen> createState() =>
      _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends ConsumerState<ProfileSettingsScreen> {
  late final TextEditingController _nameController;
  String? _errorText;

  @override
  void initState() {
    super.initState();
    final name = ref.read(authControllerProvider).user?.displayName;
    _nameController = TextEditingController(text: name ?? '치와와 여행자');
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    return MyPageDetailScaffold(
      title: '프로필 관리',
      subtitle: '여행 화면과 기록에 표시할 이름을 관리해요.',
      bottomAction: FilledButton.icon(
        key: const ValueKey('save-profile-name'),
        onPressed: _save,
        icon: const Icon(Icons.check_rounded),
        label: const Text('프로필 저장'),
      ),
      children: [
        MyPageSection(
          child: Column(
            children: [
              const MascotAvatar(size: 72),
              const SizedBox(height: ChiwawaSpacing.md),
              Text(
                auth.user?.email ?? '로그인 없이 둘러보는 중',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: ChiwawaColors.textSecondary,
                    ),
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        TextField(
          key: const ValueKey('profile-name-field'),
          controller: _nameController,
          maxLength: 20,
          textInputAction: TextInputAction.done,
          decoration: InputDecoration(
            labelText: '표시 이름',
            prefixIcon: const Icon(Icons.person_outline_rounded),
            errorText: _errorText,
          ),
          onSubmitted: (_) => _save(),
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        const MyPageStatusBanner(
          icon: Icons.info_outline_rounded,
          title: '표시 범위',
          description: '현재 여행, 일정, Memorial의 사용자 이름에 사용해요.',
        ),
      ],
    );
  }

  Future<void> _save() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      setState(() => _errorText = '표시 이름을 입력해 주세요.');
      return;
    }
    setState(() => _errorText = null);
    await ref.read(authControllerProvider.notifier).updateDisplayName(name);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('프로필 이름을 저장했어요.')),
    );
  }
}
