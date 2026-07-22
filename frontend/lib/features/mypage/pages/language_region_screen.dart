import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../widgets/my_page_detail_scaffold.dart';

class LanguageRegionScreen extends StatelessWidget {
  const LanguageRegionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return MyPageDetailScaffold(
      title: '언어 및 지역',
      subtitle: '현재 제공되는 표시 언어와 여행 정보 범위를 확인해요.',
      children: [
        const MyPageStatusBanner(
          icon: Icons.language_rounded,
          title: '현재 지원 범위',
          description: '앱 문구는 한국어, 여행 장소 정보는 일본 지역을 기준으로 제공해요.',
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageSection(
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
        const SizedBox(height: ChiwawaSpacing.lg),
        Text(
          '지원 언어와 여행 지역이 추가되면 이 화면에서 선택할 수 있어요.',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: ChiwawaColors.textSecondary,
              ),
        ),
      ],
    );
  }
}
