import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../../app/theme.dart';
import '../../../shared/widgets/app_viewport.dart';

Future<ImageSource?> showPhotoSourceSheet(BuildContext context) {
  return showModalBottomSheet<ImageSource>(
    context: context,
    useSafeArea: true,
    constraints: const BoxConstraints(maxWidth: AppLayout.maxContentWidth),
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(
        top: Radius.circular(ChiwawaRadii.sheet),
      ),
    ),
    builder: (sheetContext) => Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 44,
            height: 4,
            decoration: BoxDecoration(
              color: ChiwawaColors.border,
              borderRadius: BorderRadius.circular(ChiwawaRadii.round),
            ),
          ),
          const SizedBox(height: 16),
          ListTile(
            key: const ValueKey('photo-source-gallery'),
            leading: const Icon(Icons.photo_library),
            title: const Text('갤러리에서 선택'),
            onTap: () => Navigator.pop(sheetContext, ImageSource.gallery),
          ),
          ListTile(
            key: const ValueKey('photo-source-camera'),
            leading: const Icon(Icons.camera_alt),
            title: const Text('카메라로 촬영'),
            onTap: () => Navigator.pop(sheetContext, ImageSource.camera),
          ),
        ],
      ),
    ),
  );
}
