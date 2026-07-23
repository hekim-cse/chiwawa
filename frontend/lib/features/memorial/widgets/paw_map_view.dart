import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/memorial_map_models.dart';
import '../../../core/utils/time_formatters.dart';
import 'memorial_photo_image.dart';
import 'paw_map/paw_map_canvas.dart';
import 'paw_map/paw_map_motion.dart';
import 'paw_map/paw_map_timeline.dart';
import 'paw_photo_sheet.dart';

class PawMapView extends StatefulWidget {
  const PawMapView({
    required this.clusters,
    super.key,
  });

  final List<PawCluster> clusters;

  @override
  State<PawMapView> createState() => _PawMapViewState();
}

class _PawMapViewState extends State<PawMapView>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  bool _disableAnimations = false;
  bool _motionConfigured = false;
  bool _isComplete = false;
  PawCluster? _selectedCluster;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: PawMapMotion.totalDurationFor(widget.clusters.length),
    )..addStatusListener(_handleAnimationStatus);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final disableAnimations =
        MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (_motionConfigured && disableAnimations == _disableAnimations) return;

    _motionConfigured = true;
    _disableAnimations = disableAnimations;
    if (_disableAnimations) {
      _controller.value = 1;
    } else {
      _controller.forward(from: 0);
    }
  }

  @override
  void didUpdateWidget(covariant PawMapView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_sameClusters(oldWidget.clusters, widget.clusters)) return;

    if (_selectedCluster != null &&
        !widget.clusters.any((cluster) => cluster.id == _selectedCluster!.id)) {
      _selectedCluster = null;
    }

    _controller.duration =
        PawMapMotion.totalDurationFor(widget.clusters.length);
    if (_disableAnimations) {
      _controller.value = 1;
    } else {
      _play();
    }
  }

  @override
  void dispose() {
    _controller
      ..removeStatusListener(_handleAnimationStatus)
      ..dispose();
    super.dispose();
  }

  void _handleAnimationStatus(AnimationStatus status) {
    final isComplete = status == AnimationStatus.completed;
    if (_isComplete == isComplete || !mounted) return;
    setState(() => _isComplete = isComplete);
  }

  void _play() {
    if (_disableAnimations) {
      _controller.value = 1;
      return;
    }
    if (_isComplete || _selectedCluster != null) {
      setState(() {
        _isComplete = false;
        _selectedCluster = null;
      });
    }
    _controller.forward(from: 0);
  }

  Future<void> _openCluster(PawCluster cluster) async {
    if (_selectedCluster?.id != cluster.id) {
      setState(() => _selectedCluster = cluster);
    }
    final shouldResume = _controller.isAnimating && !_disableAnimations;
    if (shouldResume) _controller.stop();

    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: false,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(ChiwawaRadii.sheet),
        ),
      ),
      builder: (_) => PawPhotoSheet(cluster: cluster),
    );

    if (mounted && shouldResume && !_controller.isCompleted) {
      _controller.forward();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.clusters.isEmpty) {
      return const _EmptyPawMapCard();
    }

    final timeline = PawMapTimeline(markerCount: widget.clusters.length);
    final entrance = _disableAnimations
        ? const AlwaysStoppedAnimation<double>(1)
        : CurvedAnimation(
            parent: _controller,
            curve: const Interval(
              0,
              PawMapMotion.entranceEnd,
              curve: PawMapMotion.entranceCurve,
            ),
          );
    final slide = Tween<Offset>(
      begin: const Offset(0, 0.025),
      end: Offset.zero,
    ).animate(entrance);

    return FadeTransition(
      opacity: entrance,
      child: SlideTransition(
        position: slide,
        child: _PawMapCard(
          clusters: widget.clusters,
          animation: _controller,
          timeline: timeline,
          selectedCluster: _selectedCluster,
          showReplay: _isComplete && !_disableAnimations,
          onReplay: _play,
          onClusterTap: _openCluster,
        ),
      ),
    );
  }

  bool _sameClusters(List<PawCluster> a, List<PawCluster> b) {
    if (a.length != b.length) return false;
    for (var index = 0; index < a.length; index++) {
      if (a[index].id != b[index].id) return false;
    }
    return true;
  }
}

class _PawMapCard extends StatelessWidget {
  const _PawMapCard({
    required this.clusters,
    required this.animation,
    required this.timeline,
    required this.selectedCluster,
    required this.showReplay,
    required this.onReplay,
    required this.onClusterTap,
  });

  final List<PawCluster> clusters;
  final Animation<double> animation;
  final PawMapTimeline timeline;
  final PawCluster? selectedCluster;
  final bool showReplay;
  final VoidCallback onReplay;
  final ValueChanged<PawCluster> onClusterTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(
              Icons.pets_rounded,
              color: ChiwawaColors.primary,
              size: 20,
            ),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                '발자국 지도',
                style: TextStyle(
                  color: ChiwawaColors.textPrimary,
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            Text(
              '${clusters.length}곳',
              style: const TextStyle(
                color: ChiwawaColors.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        const Text(
          '사진 위치를 따라 치와와가 걸어간 하루를 보여줘요.',
          style: TextStyle(
            color: ChiwawaColors.textSecondary,
            fontSize: 12,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 14),
        PawMapCanvas(
          clusters: clusters,
          animation: animation,
          timeline: timeline,
          onClusterTap: onClusterTap,
        ),
        AnimatedSwitcher(
          duration: PawMapMotion.replayTransition,
          child: selectedCluster == null
              ? const SizedBox.shrink(
                  key: ValueKey('paw-map-selection-hidden'),
                )
              : Padding(
                  key: ValueKey(
                    'paw-map-selection-${selectedCluster!.id}',
                  ),
                  padding: const EdgeInsets.only(top: ChiwawaSpacing.sm),
                  child: _SelectedClusterPanel(
                    cluster: selectedCluster!,
                    onOpen: () => onClusterTap(selectedCluster!),
                  ),
                ),
        ),
        AnimatedSwitcher(
          duration: PawMapMotion.replayTransition,
          child: showReplay
              ? Padding(
                  key: const ValueKey('paw-map-replay-container'),
                  padding: const EdgeInsets.only(top: 12),
                  child: SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      key: const ValueKey('paw-map-replay'),
                      onPressed: onReplay,
                      icon: const Icon(Icons.replay_rounded, size: 18),
                      label: const Text('다시 보기'),
                    ),
                  ),
                )
              : const SizedBox.shrink(
                  key: ValueKey('paw-map-replay-hidden'),
                ),
        ),
      ],
    );
  }
}

class _SelectedClusterPanel extends StatelessWidget {
  const _SelectedClusterPanel({
    required this.cluster,
    required this.onOpen,
  });

  final PawCluster cluster;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final photo = cluster.photos.first;
    final time = formatTime(
      '${cluster.arrivalTime.hour}:${cluster.arrivalTime.minute}',
    );

    return Container(
      padding: const EdgeInsets.all(ChiwawaSpacing.sm),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(ChiwawaRadii.control),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(ChiwawaRadii.control),
            child: MemorialPhotoImage(
              assetPath: photo.assetPath,
              fileUrl: photo.fileUrl,
              width: 56,
              height: 56,
            ),
          ),
          const SizedBox(width: ChiwawaSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '선택 위치 · ${cluster.placeName}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: ChiwawaColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: ChiwawaSpacing.xxs),
                Text(
                  '$time · 사진 ${cluster.photoCount}장',
                  style: const TextStyle(
                    color: ChiwawaColors.textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            key: ValueKey('open-paw-photos-${cluster.id}'),
            tooltip: '사진 보기',
            onPressed: onOpen,
            icon: const Icon(Icons.chevron_right_rounded),
          ),
        ],
      ),
    );
  }
}

class _EmptyPawMapCard extends StatelessWidget {
  const _EmptyPawMapCard();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: ChiwawaSpacing.lg),
      child: Text(
        '이 날짜에는 표시할 사진 위치가 아직 없어요.',
        style: TextStyle(
          color: ChiwawaColors.textSecondary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
