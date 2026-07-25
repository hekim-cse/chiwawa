import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/settings/app_settings_controller.dart';
import '../widgets/my_page_detail_scaffold.dart';

class NotificationSettingsScreen extends ConsumerWidget {
  const NotificationSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(appSettingsProvider);
    final controller = ref.read(appSettingsProvider.notifier);
    final enabledCount = [
      settings.tripUpdatesEnabled,
      settings.memoryHighlightsEnabled,
    ].where((enabled) => enabled).length;

    return MyPageDetailScaffold(
      title: '알림 설정',
      subtitle: '이 기기에서 확인할 안내 종류를 선택해요.',
      children: [
        MyPageStatusBanner(
          icon: enabledCount == 0
              ? Icons.notifications_off_outlined
              : Icons.notifications_active_outlined,
          title: enabledCount == 0
              ? '모든 앱 안내가 꺼져 있어요'
              : '$enabledCount개 앱 안내 사용 중',
          description: '스위치를 바꾸면 선택한 설정을 이 기기에 바로 저장해요.',
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        MyPageSection(
          title: '여행 안내',
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              SwitchListTile(
                key: const ValueKey('trip-updates-switch'),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14),
                title: const Text('여행 일정 안내'),
                subtitle: const Text('현재 여행의 일정 변경 내용을 확인해요.'),
                value: settings.tripUpdatesEnabled,
                onChanged: controller.setTripUpdatesEnabled,
              ),
              const Divider(height: 1, indent: 14, endIndent: 14),
              SwitchListTile(
                key: const ValueKey('memory-highlights-switch'),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14),
                title: const Text('여행 기록 안내'),
                subtitle: const Text('정리할 사진과 여행 기록을 확인해요.'),
                value: settings.memoryHighlightsEnabled,
                onChanged: controller.setMemoryHighlightsEnabled,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageSection(
          title: '안내가 필요한 순간',
          child: Column(
            children: [
              MyPageDetailItem(
                icon: Icons.event_note_outlined,
                title: '여행 일정 안내',
                description: '현재 여행의 일정 변경과 확인할 내용을 앱 안에서 알려줘요.',
              ),
              MyPageDetailItem(
                icon: Icons.auto_awesome_outlined,
                title: '여행 기록 안내',
                description: '여행 후 정리할 사진과 Memorial 기록을 확인하도록 도와줘요.',
                showDivider: false,
              ),
            ],
          ),
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        const MyPageStatusBanner(
          icon: Icons.phone_iphone_rounded,
          title: '기기 알림 권한과는 별도예요',
          description: '현재 화면은 앱 내부 선호 설정이며 OS 알림 권한 연결은 준비 중이에요.',
          color: ChiwawaColors.warning,
        ),
      ],
    );
  }
}
