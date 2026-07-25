import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../widgets/my_page_detail_scaffold.dart';

class UserGuideScreen extends StatelessWidget {
  const UserGuideScreen({super.key});

  static const _steps = [
    _GuideStep(
      number: '01',
      title: '여행 만들기',
      description: '여행 기간과 도시를 정하고 현재 여행으로 선택해요.',
      actionLabel: '내 여행 열기',
      route: '/trips',
      icon: Icons.luggage_rounded,
      tip: '여행 기간과 도시를 먼저 정하면 홈과 일정이 같은 여행을 바라봐요.',
    ),
    _GuideStep(
      number: '02',
      title: '사진에서 장소 찾기',
      description: '사진 분석 후보와 신뢰도를 확인하고 일정 후보로 저장해요.',
      actionLabel: '사진 탐색 열기',
      route: '/explore',
      icon: Icons.camera_alt_rounded,
      tip: '랜드마크가 또렷한 사진을 사용하고 후보의 주소와 신뢰도를 함께 확인해요.',
    ),
    _GuideStep(
      number: '03',
      title: '방문 순서 설계하기',
      description: '저장한 장소를 불러와 방문 순서와 이동 흐름을 확인해요.',
      actionLabel: '일정 설계 열기',
      route: '/plan',
      icon: Icons.route_rounded,
      tip: '저장한 장소를 날짜별로 나누고 최적화 전 방문 목록을 한 번 확인해요.',
    ),
    _GuideStep(
      number: '04',
      title: '여행 기록 돌아보기',
      description: '날짜별 사진과 발자국 경로를 보고 위치정보 범위를 선택해 공유해요.',
      actionLabel: 'Memorial 열기',
      route: '/memorial',
      icon: Icons.photo_album_rounded,
      tip: '공유하기 전에 사진 위치와 위치정보 포함 여부를 다시 확인해요.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return MyPageDetailScaffold(
      title: '이용 가이드',
      subtitle: '사진 발견부터 여행 기록까지 chiwawa의 기본 흐름이에요.',
      children: [
        const MyPageStatusBanner(
          icon: Icons.flag_outlined,
          title: '4단계로 여행을 연결해요',
          description: '여행 만들기 → 장소 찾기 → 일정 설계 → 여행 기록 순서로 살펴보세요.',
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        for (var index = 0; index < _steps.length; index++) ...[
          _GuideStepCard(step: _steps[index]),
          if (index != _steps.length - 1)
            const SizedBox(height: ChiwawaSpacing.sm),
        ],
        const SizedBox(height: ChiwawaSpacing.lg),
        MyPageSection(
          title: '도움이 더 필요할 때',
          child: MyPageDetailItem(
            icon: Icons.support_agent_rounded,
            title: '문의하기',
            description: '확인한 화면과 재현 순서를 작성해 이메일로 문의할 수 있어요.',
            showDivider: false,
            onTap: () => context.push('/mypage/support'),
          ),
        ),
      ],
    );
  }
}

class _GuideStepCard extends StatelessWidget {
  const _GuideStepCard({required this.step});

  final _GuideStep step;

  @override
  Widget build(BuildContext context) {
    return MyPageSection(
      surface: true,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: ChiwawaColors.secondary,
              borderRadius: BorderRadius.circular(ChiwawaRadii.control),
            ),
            child: Icon(step.icon, color: ChiwawaColors.primary, size: 22),
          ),
          const SizedBox(width: ChiwawaSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${step.number} · ${step.title}',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: ChiwawaColors.primary,
                      ),
                ),
                const SizedBox(height: ChiwawaSpacing.xxs),
                Text(
                  step.description,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: ChiwawaColors.textSecondary,
                      ),
                ),
                const SizedBox(height: ChiwawaSpacing.xs),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.lightbulb_outline_rounded,
                      size: 16,
                      color: ChiwawaColors.primary,
                    ),
                    const SizedBox(width: ChiwawaSpacing.xxs),
                    Expanded(
                      child: Text(
                        step.tip,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: ChiwawaColors.primary,
                            ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: ChiwawaSpacing.sm),
                TextButton.icon(
                  onPressed: () => context.go(step.route),
                  icon: const Icon(Icons.arrow_forward_rounded, size: 18),
                  label: Text(step.actionLabel),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GuideStep {
  const _GuideStep({
    required this.number,
    required this.title,
    required this.description,
    required this.actionLabel,
    required this.route,
    required this.icon,
    required this.tip,
  });

  final String number;
  final String title;
  final String description;
  final String actionLabel;
  final String route;
  final IconData icon;
  final String tip;
}
