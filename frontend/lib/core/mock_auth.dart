import 'package:flutter_riverpod/flutter_riverpod.dart';

final mockAuthProvider = StateNotifierProvider<MockAuthNotifier, MockAuthState>(
  (ref) => MockAuthNotifier(),
);

class MockAuthState {
  const MockAuthState({
    this.isSignedIn = false,
    this.displayName = '치와와 여행자',
    this.email = '',
  });

  final bool isSignedIn;
  final String displayName;
  final String email;
}

class MockAuthNotifier extends StateNotifier<MockAuthState> {
  MockAuthNotifier() : super(const MockAuthState());

  void signIn({required String email, String? displayName}) {
    state = MockAuthState(
      isSignedIn: true,
      displayName: displayName?.trim().isNotEmpty == true
          ? displayName!.trim()
          : '치와와 여행자',
      email: email.trim(),
    );
  }

  void signOut() {
    state = const MockAuthState();
  }
}
