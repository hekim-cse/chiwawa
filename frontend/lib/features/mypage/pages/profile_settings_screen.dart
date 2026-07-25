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
  late String _savedName;
  String? _errorText;
  var _saving = false;
  var _saveSucceeded = false;

  @override
  void initState() {
    super.initState();
    final name = ref.read(authControllerProvider).user?.displayName;
    _savedName = name ?? '치와와 여행자';
    _nameController = TextEditingController(text: _savedName)
      ..addListener(_handleNameChanged);
  }

  @override
  void dispose() {
    _nameController.removeListener(_handleNameChanged);
    _nameController.dispose();
    super.dispose();
  }

  bool get _hasChanges => _nameController.text.trim() != _savedName;

  void _handleNameChanged() {
    if (!mounted) return;
    setState(() {
      _errorText = null;
      _saveSucceeded = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    return MyPageDetailScaffold(
      title: '프로필 관리',
      subtitle: '여행 화면과 기록에 표시할 이름을 관리해요.',
      bottomAction: FilledButton.icon(
        key: const ValueKey('save-profile-name'),
        onPressed: _saving || !_hasChanges ? null : _save,
        icon: _saving
            ? const SizedBox.square(
                dimension: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : const Icon(Icons.check_rounded),
        label: Text(_saving ? '저장 중' : '변경사항 저장'),
      ),
      children: [
        MyPageSection(
          child: Row(
            children: [
              const MascotAvatar(size: 72),
              const SizedBox(width: ChiwawaSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _savedName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: ChiwawaColors.primary,
                          ),
                    ),
                    const SizedBox(height: ChiwawaSpacing.xxs),
                    Text(
                      auth.user?.email ?? '로그인 없이 둘러보는 중',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: ChiwawaColors.textSecondary,
                          ),
                    ),
                    const SizedBox(height: ChiwawaSpacing.xxs),
                    Text(
                      auth.isSignedIn ? 'Google 계정 프로필' : '이 기기의 로컬 프로필',
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: ChiwawaColors.primary,
                          ),
                    ),
                  ],
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
            helperText: '공백을 제외하고 1~20자로 입력해 주세요.',
            prefixIcon: const Icon(Icons.person_outline_rounded),
            errorText: _errorText,
          ),
          onSubmitted: (_) => _save(),
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        MyPageStatusBanner(
          icon: _saveSucceeded
              ? Icons.check_circle_outline_rounded
              : Icons.info_outline_rounded,
          title: _saveSucceeded ? '변경사항 저장됨' : '현재 표시 이름: $_savedName',
          description: _saveSucceeded
              ? '마이페이지와 사용자 이름이 필요한 화면에 바로 반영했어요.'
              : '저장 전에는 현재 이름을 그대로 사용해요.',
          color: _saveSucceeded ? ChiwawaColors.success : ChiwawaColors.primary,
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageSection(
          title: '이 이름이 표시되는 곳',
          child: Column(
            children: [
              MyPageDetailItem(
                icon: Icons.person_outline_rounded,
                title: '마이페이지 프로필',
                description: '프로필과 계정 정보의 대표 이름으로 표시해요.',
              ),
              MyPageDetailItem(
                icon: Icons.luggage_outlined,
                title: '여행 화면과 기록',
                description: '현재 여행과 Memorial의 사용자 정보에 사용해요.',
              ),
              MyPageDetailItem(
                icon: Icons.devices_outlined,
                title: '저장 범위',
                description: '현재는 이 기기에 저장하며 프로필 수정 API는 연결 전이에요.',
                showDivider: false,
              ),
            ],
          ),
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
    setState(() {
      _errorText = null;
      _saving = true;
    });
    await ref.read(authControllerProvider.notifier).updateDisplayName(name);
    if (!mounted) return;
    setState(() {
      _savedName = name;
      _saving = false;
      _saveSucceeded = true;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('프로필 이름을 저장했어요.')),
    );
  }
}
