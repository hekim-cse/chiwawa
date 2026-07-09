import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../app/theme.dart';
import '../../core/models/travel_models.dart';
import '../../core/providers/data_providers.dart';
import '../../core/repositories/photo_place_repository.dart';
import '../../core/saved_photo_places.dart';
import '../../shared/widgets/async_value_view.dart';
import 'widgets/photo_upload_zone.dart';
import 'widgets/place_result_card.dart';

final exploreImagePathProvider = StateProvider<String?>((ref) => null);
final exploreAnalyzingProvider = StateProvider<bool>((ref) => false);
final exploreResultVisibleProvider = StateProvider<bool>((ref) => false);
final exploreSelectedResultProvider = StateProvider<PhotoSearchResult>(
  (ref) => ref.watch(photoPlaceRepositoryProvider).defaultResult,
);

class ExploreScreen extends ConsumerStatefulWidget {
  const ExploreScreen({super.key});

  @override
  ConsumerState<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends ConsumerState<ExploreScreen> {
  final _picker = ImagePicker();

  void _savePlaceToPlan(PhotoSearchResult result) {
    final added = ref.read(savedPhotoPlacesProvider.notifier).addPlace(result);

    final messenger = ScaffoldMessenger.of(context)..hideCurrentSnackBar();
    messenger.showSnackBar(
      SnackBar(
        content: Text(
          added
              ? '${result.name} 일정 후보에 저장했어요.'
              : '${result.name} 이미 저장된 장소예요.',
        ),
      ),
    );
  }

  void _showRecentResult(PhotoSearchResult result) {
    ref.read(exploreSelectedResultProvider.notifier).state = result;
    ref.read(exploreImagePathProvider.notifier).state = null;
    ref.read(exploreAnalyzingProvider.notifier).state = false;
    ref.read(exploreResultVisibleProvider.notifier).state = true;
  }

  Future<void> _openSourceDialog() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 44,
                height: 4,
                decoration: BoxDecoration(
                  color: ChiwawaColors.border,
                  borderRadius: BorderRadius.circular(99),
                ),
              ),
              const SizedBox(height: 16),
              ListTile(
                leading: const Icon(Icons.photo_library),
                title: const Text('갤러리에서 선택'),
                onTap: () => Navigator.pop(context, ImageSource.gallery),
              ),
              ListTile(
                leading: const Icon(Icons.camera_alt),
                title: const Text('카메라로 촬영'),
                onTap: () => Navigator.pop(context, ImageSource.camera),
              ),
            ],
          ),
        ),
      ),
    );

    if (source == null) return;

    final picked = await _picker.pickImage(source: source, imageQuality: 80);
    if (!mounted || picked == null) return;

    ref.read(exploreImagePathProvider.notifier).state = picked.path;
    ref.read(exploreAnalyzingProvider.notifier).state = true;
    ref.read(exploreResultVisibleProvider.notifier).state = false;

    try {
      final result = await ref.read(photoPlaceRepositoryProvider).analyzePhoto(
            picked.path,
          );
      if (!mounted) return;

      ref.read(exploreSelectedResultProvider.notifier).state = result;
      ref.read(exploreResultVisibleProvider.notifier).state = true;
    } catch (_) {
      if (!mounted) return;

      ref.read(exploreResultVisibleProvider.notifier).state = false;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('사진 분석은 아직 준비 중이에요.')),
      );
    } finally {
      if (mounted) {
        ref.read(exploreAnalyzingProvider.notifier).state = false;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final imagePath = ref.watch(exploreImagePathProvider);
    final isAnalyzing = ref.watch(exploreAnalyzingProvider);
    final showResult = ref.watch(exploreResultVisibleProvider);
    final selectedResult = ref.watch(exploreSelectedResultProvider);
    final savedPlaces = ref.watch(savedPhotoPlacesProvider);
    final recentSearchesAsync = ref.watch(recentPhotoSearchesProvider);
    final selectedResultSaved = savedPlaces.any(
      (place) => place.name == selectedResult.name,
    );

    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 96),
        children: [
          Text(
            '사진으로 찾아가기',
            style: Theme.of(context)
                .textTheme
                .titleLarge
                ?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 6),
          const Text(
            '사진을 올리면 장소를 인식하고 경로를 제안해요.',
            style: TextStyle(color: ChiwawaColors.textSecondary),
          ),
          const SizedBox(height: 18),
          PhotoUploadZone(onTap: _openSourceDialog),
          if (isAnalyzing) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(color: ChiwawaColors.primary),
          ],
          if (showResult) ...[
            const SizedBox(height: 18),
            PlaceResultCard(
              result: selectedResult,
              imageFile: imagePath == null ? null : File(imagePath),
              isSaved: selectedResultSaved,
              onAddToPlan: () => _savePlaceToPlan(selectedResult),
            ),
          ],
          const SizedBox(height: 26),
          Text(
            '최근 탐색',
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 12),
          AsyncValueView<List<PhotoSearchResult>>(
            value: recentSearchesAsync,
            loadingHeight: 142,
            onRetry: () => ref.invalidate(recentPhotoSearchesProvider),
            builder: (recentSearches) => SizedBox(
              height: 142,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: recentSearches.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, index) {
                  final item = recentSearches[index];
                  return _RecentSearchCard(
                    item: item,
                    index: index,
                    onTap: () => _showRecentResult(item),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RecentSearchCard extends StatelessWidget {
  const _RecentSearchCard({
    required this.item,
    required this.index,
    required this.onTap,
  });

  final PhotoSearchResult item;
  final int index;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: ChiwawaColors.border),
      ),
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          width: 128,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                height: 86,
                width: double.infinity,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: index.isEven
                        ? const [Color(0xFFFFD7DF), Color(0xFFFFF1C7)]
                        : const [Color(0xFFFFE6EC), Color(0xFFEAF7FF)],
                  ),
                ),
                child: const Icon(
                  Icons.photo_camera_rounded,
                  color: ChiwawaColors.primary,
                  size: 30,
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(10),
                child: Text(
                  item.name,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
