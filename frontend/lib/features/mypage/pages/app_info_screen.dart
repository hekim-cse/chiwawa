import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/env.dart';
import '../../../shared/widgets/mascot_avatar.dart';
import '../my_page_routes.dart';
import '../widgets/my_page_detail_scaffold.dart';

class AppInfoScreen extends StatelessWidget {
  const AppInfoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const platformLabel = kIsWeb ? 'Web' : 'App';
    const dataModeLabel = useApiBackend ? 'API 연결 모드' : 'Mock 데모 모드';

    return MyPageDetailScaffold(
      title: '앱 정보',
      subtitle: '현재 설치된 chiwawa 프론트 버전과 지원 환경을 확인해요.',
      children: [
        MyPageSection(
          child: Column(
            children: [
              const MascotAvatar(size: 72),
              const SizedBox(height: ChiwawaSpacing.sm),
              Text(
                'chiwawa',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: ChiwawaColors.primary,
                    ),
              ),
              const SizedBox(height: ChiwawaSpacing.xxs),
              Text(
                '사진에서 찾은 장소를 일정과 여행 기록으로 연결해요.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: ChiwawaColors.textSecondary,
                    ),
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageSection(
          title: '버전 정보',
          child: Column(
            children: [
              MyPageInfoRow(label: '버전', value: '1.0.0'),
              MyPageInfoRow(label: '빌드 SHA', value: appBuildSha),
              MyPageInfoRow(label: '현재 실행 환경', value: platformLabel),
              MyPageInfoRow(label: '데이터 연결', value: dataModeLabel),
              MyPageInfoRow(
                label: '지원 환경',
                value: 'App · Web',
                showDivider: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageSection(
          title: 'chiwawa로 할 수 있는 일',
          child: Column(
            children: [
              MyPageDetailItem(
                icon: Icons.camera_alt_outlined,
                title: '사진에서 장소 찾기',
                description: '사진 분석 후보를 비교하고 일정 후보로 저장해요.',
              ),
              MyPageDetailItem(
                icon: Icons.route_outlined,
                title: 'AI 일정 설계',
                description: '선택한 장소의 방문 순서와 이동 흐름을 정리해요.',
              ),
              MyPageDetailItem(
                icon: Icons.photo_album_outlined,
                title: 'Memorial 여행 기록',
                description: '날짜별 사진과 발자국 경로로 여행을 돌아봐요.',
                showDivider: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageStatusBanner(
          icon: useApiBackend
              ? Icons.cloud_done_outlined
              : Icons.science_outlined,
          title: dataModeLabel,
          description: useApiBackend
              ? 'Repository가 API 구현체를 사용하도록 실행된 상태예요.'
              : '서버 없이 핵심 여행 흐름을 확인할 수 있는 데모 상태예요.',
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: () => context.push(MyPageRoutes.privacy),
            icon: const Icon(Icons.privacy_tip_outlined),
            label: const Text('개인정보 및 위치 정보 안내'),
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.xs),
        TextButton.icon(
          onPressed: () => context.push(MyPageRoutes.support),
          icon: const Icon(Icons.support_agent_rounded),
          label: const Text('앱 이용 문의하기'),
        ),
      ],
    );
  }
}
