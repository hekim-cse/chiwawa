enum TransportMode { walk, drive, transit }

extension TransportModeMapping on TransportMode {
  String get label {
    return switch (this) {
      TransportMode.walk => '도보',
      TransportMode.drive => '자동차',
      TransportMode.transit => '대중교통',
    };
  }

  /// FastAPI/백엔드 요청에 사용하는 소문자 코드.
  String get backendCode => name;

  /// AI route_planner 계약에 사용하는 대문자 코드.
  String get aiCode => name.toUpperCase();

  static TransportMode? tryFromWireCode(String? code) {
    if (code == null) return null;
    final normalized = code.trim().toLowerCase();
    for (final mode in TransportMode.values) {
      if (mode.backendCode == normalized) return mode;
    }
    return null;
  }

  static TransportMode fromBackendCode(
    String? code, {
    TransportMode fallback = TransportMode.transit,
  }) {
    return tryFromWireCode(code) ?? fallback;
  }

  static TransportMode fromAiCode(
    String? code, {
    TransportMode fallback = TransportMode.transit,
  }) {
    return tryFromWireCode(code) ?? fallback;
  }
}
