import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../my_page_routes.dart';
import '../widgets/my_page_detail_scaffold.dart';

class AppInfoScreen extends StatelessWidget {
  const AppInfoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return MyPageDetailScaffold(
      title: '앱 정보',
      subtitle: '현재 설치된 chiwawa 프론트 버전과 지원 환경을 확인해요.',
      children: [
        MyPageSection(
          child: Column(
            children: [
              Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  color: ChiwawaColors.secondary,
                  borderRadius: BorderRadius.circular(ChiwawaRadii.card),
                ),
                child: const Icon(
                  Icons.pets_rounded,
                  color: ChiwawaColors.primary,
                  size: 28,
                ),
              ),
              const SizedBox(height: ChiwawaSpacing.sm),
              Text('chiwawa', style: Theme.of(context).textTheme.titleLarge),
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
              MyPageInfoRow(label: '지원 환경', value: 'App · Web'),
              MyPageInfoRow(
                label: '화면 언어',
                value: '한국어',
                showDivider: false,
              ),
            ],
          ),
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
      ],
    );
  }
}
