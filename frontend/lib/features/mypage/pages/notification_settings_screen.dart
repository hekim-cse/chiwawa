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

    return MyPageDetailScaffold(
      title: '알림 설정',
      subtitle: '이 기기에서 확인할 안내 종류를 선택해요.',
      children: [
        const MyPageStatusBanner(
          icon: Icons.save_outlined,
          title: '변경 즉시 저장',
          description: '선택한 안내 설정을 이 기기에 저장해요.',
        ),
        const SizedBox(height: ChiwawaSpacing.lg),
        MyPageSection(
          title: '여행 안내',
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              SwitchListTile.adaptive(
                key: const ValueKey('trip-updates-switch'),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14),
                title: const Text('여행 일정 안내'),
                subtitle: const Text('현재 여행의 일정 변경 내용을 확인해요.'),
                value: settings.tripUpdatesEnabled,
                onChanged: controller.setTripUpdatesEnabled,
              ),
              const Divider(height: 1, indent: 14, endIndent: 14),
              SwitchListTile.adaptive(
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
      ],
    );
  }
}
