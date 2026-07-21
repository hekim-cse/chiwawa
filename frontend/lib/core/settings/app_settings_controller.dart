import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppSettingsState {
  const AppSettingsState({
    this.tripUpdatesEnabled = true,
    this.memoryHighlightsEnabled = true,
  });

  final bool tripUpdatesEnabled;
  final bool memoryHighlightsEnabled;

  AppSettingsState copyWith({
    bool? tripUpdatesEnabled,
    bool? memoryHighlightsEnabled,
  }) {
    return AppSettingsState(
      tripUpdatesEnabled: tripUpdatesEnabled ?? this.tripUpdatesEnabled,
      memoryHighlightsEnabled:
          memoryHighlightsEnabled ?? this.memoryHighlightsEnabled,
    );
  }
}

final appSettingsProvider =
    StateNotifierProvider<AppSettingsController, AppSettingsState>((ref) {
  final controller = AppSettingsController();
  unawaited(controller.restore());
  return controller;
});

class AppSettingsController extends StateNotifier<AppSettingsState> {
  AppSettingsController() : super(const AppSettingsState());

  static const _tripUpdatesKey = 'settings_trip_updates';
  static const _memoryHighlightsKey = 'settings_memory_highlights';
  Future<void>? _restoreTask;
  Future<void> _saveTail = Future<void>.value();
  int _mutationVersion = 0;

  Future<void> restore() => _restoreTask ??= _restore();

  Future<void> _restore() async {
    final restoreVersion = _mutationVersion;
    try {
      final prefs = await SharedPreferences.getInstance();
      if (!mounted || restoreVersion != _mutationVersion) return;
      state = AppSettingsState(
        tripUpdatesEnabled: prefs.getBool(_tripUpdatesKey) ?? true,
        memoryHighlightsEnabled: prefs.getBool(_memoryHighlightsKey) ?? true,
      );
    } catch (_) {
      // 저장소 미지원 환경에서는 기본값을 유지한다.
    }
  }

  Future<void> setTripUpdatesEnabled(bool enabled) async {
    _mutationVersion += 1;
    state = state.copyWith(tripUpdatesEnabled: enabled);
    await _save(_tripUpdatesKey, enabled);
  }

  Future<void> setMemoryHighlightsEnabled(bool enabled) async {
    _mutationVersion += 1;
    state = state.copyWith(memoryHighlightsEnabled: enabled);
    await _save(_memoryHighlightsKey, enabled);
  }

  Future<void> _save(String key, bool value) {
    final operation = _saveTail.then((_) => _writeValue(key, value));
    _saveTail = operation;
    return operation;
  }

  Future<void> _writeValue(String key, bool value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(key, value);
    } catch (_) {
      // 현재 실행 중 상태는 유지한다.
    }
  }
}
