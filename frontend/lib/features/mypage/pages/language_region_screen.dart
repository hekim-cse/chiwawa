import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../widgets/my_page_detail_scaffold.dart';

class LanguageRegionScreen extends StatelessWidget {
  const LanguageRegionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const MyPageDetailScaffold(
      title: '언어 및 지역',
      subtitle: '현재 제공되는 표시 언어와 여행 정보 범위를 확인해요.',
      children: [
        MyPageStatusBanner(
          icon: Icons.language_rounded,
          title: '현재 지원 범위',
          description: '앱 문구는 한국어, 여행 장소 정보는 일본 지역을 기준으로 제공해요.',
        ),
        SizedBox(height: ChiwawaSpacing.lg),
        MyPageSection(
          title: '표시 설정',
          child: Column(
            children: [
              MyPageInfoRow(label: '표시 언어', value: '한국어'),
              MyPageInfoRow(label: '여행 지역', value: '일본'),
              MyPageInfoRow(
                label: '시간 표기',
                value: '24시간제',
                showDivider: false,
              ),
            ],
          ),
        ),
        SizedBox(height: ChiwawaSpacing.lg),
        MyPageSection(
          title: '표기 예시',
          child: Column(
            children: [
              MyPageInfoRow(label: '날짜', value: '2025. 4. 1. (화)'),
              MyPageInfoRow(label: '시간', value: '09:30'),
              MyPageInfoRow(label: '거리', value: '3.8km'),
              MyPageInfoRow(
                label: '현지 금액',
                value: '¥1,240',
                showDivider: false,
              ),
            ],
          ),
        ),
        SizedBox(height: ChiwawaSpacing.lg),
        MyPageStatusBanner(
          icon: Icons.tune_rounded,
          title: '선택 기능 준비 중',
          description:
              '현재 버전은 한국어와 일본 여행 형식으로 고정되어 있어요. 지원 범위가 늘어나면 이 화면에서 선택할 수 있어요.',
          color: ChiwawaColors.warning,
        ),
      ],
    );
  }
}
