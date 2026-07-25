import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/auth/auth_controller.dart';
import '../widgets/my_page_detail_scaffold.dart';

class AccountSettingsScreen extends ConsumerWidget {
  const AccountSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final signedIn = auth.isSignedIn;

    return MyPageDetailScaffold(
      title: '계정 연결',
      subtitle: '여행 데이터를 이어서 사용할 계정 상태를 확인해요.',
      bottomAction: SizedBox(
        width: double.infinity,
        child: signedIn
            ? OutlinedButton.icon(
                key: const ValueKey('account-logout'),
                onPressed: () => _confirmSignOut(context, ref),
                icon: const Icon(Icons.logout_rounded),
                label: const Text('로그아웃'),
              )
            : FilledButton.icon(
                key: const ValueKey('connect-google-account'),
                onPressed: () => context.go('/auth'),
                icon: const Icon(Icons.account_circle_rounded),
                label: const Text('Google 계정 연결'),
              ),
      ),
      children: [
        MyPageStatusBanner(
          icon: signedIn
              ? Icons.verified_user_rounded
              : Icons.person_outline_rounded,
          title: signedIn ? 'Google 계정 연결됨' : '게스트로 이용 중',
          description: signedIn
              ? '${auth.user?.email ?? 'Google 계정'}으로 로그인한 상태예요.'
              : '계정 동기화 없이 현재 기기의 로컬 상태를 사용해요.',
          color: signedIn ? ChiwawaColors.success : ChiwawaColors.primary,
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        MyPageSection(
          title: '계정 정보',
          child: Column(
            children: [
              MyPageInfoRow(
                label: '이름',
                value: auth.user?.displayName ?? '치와와 여행자',
              ),
              MyPageInfoRow(
                label: '이메일',
                value: auth.user?.email ?? '연결되지 않음',
              ),
              MyPageInfoRow(
                label: '로그인 방식',
                value: signedIn ? 'Google OAuth' : '게스트',
                showDivider: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        MyPageSection(
          title: '데이터 보관 방식',
          child: Column(
            children: [
              MyPageDetailItem(
                icon: signedIn
                    ? Icons.cloud_done_outlined
                    : Icons.phone_iphone_rounded,
                title: signedIn ? '계정으로 이용 중' : '이 기기에서 둘러보기',
                description: signedIn
                    ? '앱은 현재 Google 계정을 기준으로 로그인 상태를 구분해요.'
                    : '표시 이름과 알림 설정을 이 기기에 저장해요.',
              ),
              MyPageDetailItem(
                icon: Icons.sync_lock_outlined,
                title: '서버 동기화 범위',
                description: signedIn
                    ? '실제 여행 데이터 동기화는 서버 API 연결 상태에 따라 달라져요.'
                    : '게스트 상태에서는 다른 기기로 자동 동기화되지 않아요.',
              ),
              MyPageDetailItem(
                icon: Icons.logout_rounded,
                title: signedIn ? '로그아웃 시' : '계정 연결 시',
                description: signedIn
                    ? '계정 연결을 해제하며 여행 삭제 작업과는 별개예요.'
                    : '로그인 화면에서 Google 계정 연결을 시작할 수 있어요.',
                showDivider: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        Text(
          signedIn
              ? '로그인 상태가 만료되면 계정을 다시 연결해 주세요.'
              : '계정을 연결하지 않아도 Mock 여행 기능은 계속 둘러볼 수 있어요.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: ChiwawaColors.textSecondary,
              ),
        ),
      ],
    );
  }

  Future<void> _confirmSignOut(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('로그아웃할까요?'),
        content: const Text('이 기기의 계정 연결을 해제하고 로그인 화면으로 이동해요.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('로그아웃'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await ref.read(authControllerProvider.notifier).signOut();
  }
}
