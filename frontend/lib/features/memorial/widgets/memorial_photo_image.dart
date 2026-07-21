import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/providers/data_providers.dart';

class MemorialPhotoImage extends ConsumerWidget {
  const MemorialPhotoImage({
    required this.assetPath,
    required this.fileUrl,
    required this.width,
    required this.height,
    this.fit = BoxFit.cover,
    super.key,
  });

  final String assetPath;
  final String fileUrl;
  final double width;
  final double height;
  final BoxFit fit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (assetPath.isNotEmpty) {
      return Image.asset(
        assetPath,
        width: width,
        height: height,
        cacheWidth: (width * 2).round(),
        fit: fit,
        errorBuilder: (context, error, stackTrace) =>
            MemorialPhotoPlaceholder(width: width, height: height),
      );
    }

    if (fileUrl.isEmpty) {
      return MemorialPhotoPlaceholder(width: width, height: height);
    }

    return ref.watch(memorialPhotoBytesProvider(fileUrl)).when(
          data: (bytes) => bytes.isEmpty
              ? MemorialPhotoPlaceholder(width: width, height: height)
              : Image.memory(
                  bytes,
                  key: ValueKey('memorial-photo-$fileUrl'),
                  width: width,
                  height: height,
                  cacheWidth: (width * 2).round(),
                  fit: fit,
                  gaplessPlayback: true,
                  errorBuilder: (context, error, stackTrace) =>
                      MemorialPhotoPlaceholder(width: width, height: height),
                ),
          loading: () => MemorialPhotoPlaceholder(
            width: width,
            height: height,
            loading: true,
          ),
          error: (error, stackTrace) =>
              MemorialPhotoPlaceholder(width: width, height: height),
        );
  }
}

class MemorialPhotoPlaceholder extends StatelessWidget {
  const MemorialPhotoPlaceholder({
    required this.width,
    required this.height,
    this.loading = false,
    super.key,
  });

  final double width;
  final double height;
  final bool loading;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      color: ChiwawaColors.secondary,
      alignment: Alignment.center,
      child: loading
          ? const SizedBox.square(
              dimension: 20,
              child: CircularProgressIndicator(
                color: ChiwawaColors.primary,
                strokeWidth: 2,
              ),
            )
          : const Icon(
              Icons.photo_rounded,
              color: ChiwawaColors.primary,
            ),
    );
  }
}
