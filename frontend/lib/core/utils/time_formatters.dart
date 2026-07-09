String formatTime(String value) {
  final trimmed = value.trim();
  final parts = trimmed.split(':');

  if (parts.length < 2) {
    return trimmed;
  }

  final hour = parts[0].padLeft(2, '0');
  final minute = parts[1].padLeft(2, '0');
  return '$hour:$minute';
}
