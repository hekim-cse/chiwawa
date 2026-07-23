import 'dart:typed_data';

class PhotoUpload {
  const PhotoUpload({
    required this.bytes,
    required this.fileName,
    required this.mimeType,
    required this.previewPath,
  });

  final Uint8List bytes;
  final String fileName;
  final String mimeType;
  final String previewPath;

  bool get isEmpty => bytes.isEmpty;
}
