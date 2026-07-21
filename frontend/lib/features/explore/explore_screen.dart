import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/theme.dart';
import '../../core/models/travel_models.dart';
import '../../core/providers/data_providers.dart';
import '../../core/saved_photo_places.dart';
import '../../shared/widgets/app_viewport.dart';
import '../../shared/widgets/app_page_header.dart';
import 'explore_controller.dart';
import 'widgets/candidate_selector.dart';
import 'widgets/explore_analysis_failure.dart';
import 'widgets/photo_source_sheet.dart';
import 'widgets/photo_upload_zone.dart';
import 'widgets/place_correction_sheet.dart';
import 'widgets/place_result_card.dart';
import 'widgets/recent_searches_section.dart';

export 'explore_controller.dart'
    show
        exploreImagePathProvider,
        exploreAnalyzingProvider,
        exploreResultVisibleProvider,
        exploreAnalysisErrorProvider,
        exploreSelectedResultProvider,
        exploreCandidatesProvider,
        exploreControllerProvider;

class ExploreScreen extends ConsumerStatefulWidget {
  const ExploreScreen({super.key});

  @override
  ConsumerState<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends ConsumerState<ExploreScreen> {
  final _picker = ImagePicker();

  @override
  Widget build(BuildContext context) {
    final imagePath = ref.watch(exploreImagePathProvider);
    final isAnalyzing = ref.watch(exploreAnalyzingProvider);
    final showResult = ref.watch(exploreResultVisibleProvider);
    final analysisError = ref.watch(exploreAnalysisErrorProvider);
    final selectedResult = ref.watch(exploreSelectedResultProvider);
    final candidates = ref.watch(exploreCandidatesProvider);
    ref.watch(savedPhotoPlacesProvider);
    final selectedResultSaved = ref
        .read(savedPhotoPlacesProvider.notifier)
        .containsPlace(selectedResult);

    return SafeArea(
      child: ListView(
        padding: AppLayout.pageInsets(context),
        children: [
          const AppPageHeader(
            title: '사진으로 찾아가기',
            subtitle: '사진 속 장소를 비교하고 여행 일정으로 이어보세요.',
          ),
          const SizedBox(height: 18),
          PhotoUploadZone(
            onTap: _pickAndAnalyzePhoto,
            compact: showResult || imagePath != null,
          ),
          if (isAnalyzing) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(color: ChiwawaColors.primary),
          ],
          if (analysisError != null && !isAnalyzing) ...[
            const SizedBox(height: 18),
            ExploreAnalysisFailure(
              message: analysisError,
              canRetry: imagePath != null,
              onRetry: _retryAnalysis,
              onChooseAnother: _pickAndAnalyzePhoto,
            ),
          ],
          if (showResult) ...[
            const SizedBox(height: 18),
            if (candidates.length > 1) ...[
              CandidateSelector(
                candidates: candidates,
                selected: selectedResult,
                onSelected: ref.read(exploreControllerProvider).selectCandidate,
              ),
              const SizedBox(height: 12),
            ],
            PlaceResultCard(
              key: ValueKey('place-result-${selectedResult.identityKey}'),
              result: selectedResult,
              imagePath: imagePath,
              isSaved: selectedResultSaved,
              onEdit: () => _editSelectedPlace(selectedResult),
              onDirections: () => _openDirections(selectedResult),
              onAddToPlan: () => _savePlaceToPlan(selectedResult),
            ),
          ],
          const SizedBox(height: 26),
          RecentSearchesSection(
            value: ref.watch(recentPhotoSearchesProvider),
            onRetry: () => ref.invalidate(recentPhotoSearchesProvider),
            onSelected: ref.read(exploreControllerProvider).showRecentResult,
          ),
        ],
      ),
    );
  }

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

  Future<void> _editSelectedPlace(PhotoSearchResult result) async {
    final updated = await showPlaceCorrectionSheet(context, result: result);
    if (updated == null || !mounted) return;
    ref.read(exploreControllerProvider).replaceSelectedCandidate(updated);
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(content: Text('선택한 장소 정보를 수정했어요.')));
  }

  Future<void> _pickAndAnalyzePhoto() async {
    final source = await showPhotoSourceSheet(context);
    if (source == null) return;

    final picked = await _picker.pickImage(source: source, imageQuality: 80);
    if (!mounted || picked == null) return;

    final succeeded =
        await ref.read(exploreControllerProvider).analyzePhoto(picked.path);
    if (!mounted || succeeded) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('사진 분석에 실패했어요. 다시 시도해 주세요.')),
    );
  }

  Future<void> _retryAnalysis() async {
    final imagePath = ref.read(exploreImagePathProvider);
    if (imagePath == null) {
      await _pickAndAnalyzePhoto();
      return;
    }

    await ref.read(exploreControllerProvider).analyzePhoto(imagePath);
  }

  Future<void> _openDirections(PhotoSearchResult result) async {
    final destination = result.latitude != null && result.longitude != null
        ? '${result.latitude},${result.longitude}'
        : result.address;
    final uri = Uri.https(
      'www.google.com',
      '/maps/dir/',
      {'api': '1', 'destination': destination},
    );
    try {
      final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (opened || !mounted) return;
    } catch (_) {
      if (!mounted) return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('외부 지도를 열지 못했어요.')),
    );
  }
}
