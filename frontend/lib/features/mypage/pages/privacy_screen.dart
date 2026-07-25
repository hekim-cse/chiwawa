import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../shared/widgets/app_list_group.dart';
import '../my_page_routes.dart';
import '../widgets/my_page_detail_scaffold.dart';

class PrivacyScreen extends StatelessWidget {
  const PrivacyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return MyPageDetailScaffold(
      title: '개인정보 및 위치 정보',
      subtitle: '사진과 위치 정보가 어떤 화면에서 사용되는지 확인해요.',
      children: [
        const MyPageStatusBanner(
          icon: Icons.location_off_outlined,
          title: '공유 위치정보 기본값: 포함 안 함',
          description: 'Memorial을 공유할 때 사용자가 직접 포함으로 바꾼 경우에만 위치를 넣어요.',
          color: ChiwawaColors.success,
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const AppListGroup(
          children: [
            AppListRow(
              title: '사진',
              titleColor: ChiwawaColors.primary,
              subtitle: '장소 후보를 찾고 날짜별 여행 기록을 구성하는 데 사용해요.',
              leading: AppLeadingIcon(icon: Icons.photo_outlined),
            ),
            AppListRow(
              title: '위치',
              titleColor: ChiwawaColors.primary,
              subtitle: '지도와 이동 경로를 표시하며 좌표가 없는 사진은 사진 목록에만 남겨요.',
              leading: AppLeadingIcon(icon: Icons.location_on_outlined),
            ),
            AppListRow(
              title: '계정',
              titleColor: ChiwawaColors.primary,
              subtitle: '로그인 정보는 내 여행 데이터를 다른 사용자와 구분하고 보호하는 데 사용해요.',
              leading: AppLeadingIcon(icon: Icons.account_circle_outlined),
              showDivider: false,
            ),
          ],
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageSection(
          title: '내가 직접 관리할 수 있는 항목',
          child: Column(
            children: [
              MyPageDetailItem(
                icon: Icons.hide_image_outlined,
                title: '사진 제외와 복원',
                description: 'Memorial 편집에서 기록에 포함할 사진을 직접 고를 수 있어요.',
              ),
              MyPageDetailItem(
                icon: Icons.edit_location_alt_outlined,
                title: '사진 위치 수정',
                description: '장소가 다르면 Memorial에서 사진의 위치를 바로잡을 수 있어요.',
              ),
              MyPageDetailItem(
                icon: Icons.share_location_outlined,
                title: '공유 위치정보 선택',
                description: '공유할 때만 위치정보 포함 여부를 선택하며 기본값은 포함 안 함이에요.',
                showDivider: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageSection(
          title: '정보가 사용되는 흐름',
          child: Column(
            children: [
              MyPageInfoRow(label: '1. 선택', value: '사용자가 사진을 직접 선택'),
              MyPageInfoRow(label: '2. 앱 안에서', value: '장소 후보·지도·기록 구성'),
              MyPageInfoRow(
                label: '3. 공유할 때',
                value: '위치정보 포함 여부 재확인',
                showDivider: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: () => context.go('/memorial'),
            icon: const Icon(Icons.photo_album_outlined),
            label: const Text('Memorial 공유 설정 확인'),
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.sm),
        Text(
          '현재는 여행 기록을 공유할 때 위치정보 포함 여부를 직접 선택할 수 있어요.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: ChiwawaColors.textSecondary,
              ),
        ),
        const SizedBox(height: ChiwawaSpacing.xs),
        TextButton.icon(
          onPressed: () => context.push(MyPageRoutes.support),
          icon: const Icon(Icons.support_agent_rounded),
          label: const Text('개인정보 관련 문의하기'),
        ),
      ],
    );
  }
}
