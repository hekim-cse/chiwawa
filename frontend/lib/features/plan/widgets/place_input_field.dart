import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/place_search_models.dart';
import '../models/plan_place_selection.dart';
import '../plan_place_search_controller.dart';

class PlaceInputField extends StatefulWidget {
  const PlaceInputField({
    required this.places,
    required this.searchState,
    required this.onQueryChanged,
    required this.onPlaceSelected,
    required this.onRetry,
    required this.onRemove,
    super.key,
  });

  final List<PlanPlaceSelection> places;
  final PlanPlaceSearchState searchState;
  final ValueChanged<String> onQueryChanged;
  final ValueChanged<PlaceSearchCandidate> onPlaceSelected;
  final VoidCallback onRetry;
  final ValueChanged<PlanPlaceSelection> onRemove;

  @override
  State<PlaceInputField> createState() => _PlaceInputFieldState();
}

class _PlaceInputFieldState extends State<PlaceInputField> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.searchState.query);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant PlaceInputField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_controller.text == widget.searchState.query) return;
    _controller.value = TextEditingValue(
      text: widget.searchState.query,
      selection: TextSelection.collapsed(
        offset: widget.searchState.query.length,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _controller,
            textInputAction: TextInputAction.search,
            onChanged: widget.onQueryChanged,
            decoration: InputDecoration(
              hintText: '방문 장소를 검색하세요',
              prefixIcon: const Icon(Icons.search),
              filled: true,
              fillColor: ChiwawaColors.background,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(ChiwawaRadii.control),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          _buildSearchFeedback(context),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (var index = 0; index < widget.places.length; index++)
                InputChip(
                  key: ValueKey(
                    'selected-place-${widget.places[index].id}',
                  ),
                  label: Text(widget.places[index].name),
                  selected: true,
                  selectedColor: ChiwawaColors.secondary,
                  checkmarkColor: ChiwawaColors.primary,
                  deleteIconColor: ChiwawaColors.primary,
                  labelStyle: const TextStyle(
                    color: ChiwawaColors.primary,
                    fontWeight: FontWeight.w800,
                  ),
                  deleteButtonTooltipMessage: '${widget.places[index].name} 삭제',
                  onDeleted: () => widget.onRemove(widget.places[index]),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSearchFeedback(BuildContext context) {
    return switch (widget.searchState.status) {
      PlanPlaceSearchStatus.idle => const SizedBox.shrink(),
      PlanPlaceSearchStatus.loading => const Padding(
          padding: EdgeInsets.only(top: ChiwawaSpacing.xs),
          child: LinearProgressIndicator(minHeight: 2),
        ),
      PlanPlaceSearchStatus.success => Column(
          children: [
            for (final candidate in widget.searchState.results)
              ListTile(
                key: ValueKey(
                  'visit-place-result-${candidate.providerPlaceId}',
                ),
                title: Text(candidate.name),
                subtitle: Text(candidate.formattedAddress),
                trailing: const Icon(Icons.add_circle_outline_rounded),
                onTap: () => widget.onPlaceSelected(candidate),
              ),
          ],
        ),
      PlanPlaceSearchStatus.empty => const Padding(
          padding: EdgeInsets.only(top: ChiwawaSpacing.xs),
          child: Text('검색 결과가 없어요. 장소 이름을 더 자세히 입력해 주세요.'),
        ),
      PlanPlaceSearchStatus.failure => Padding(
          padding: const EdgeInsets.only(top: ChiwawaSpacing.xs),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  widget.searchState.message ?? '장소를 검색하지 못했어요.',
                ),
              ),
              TextButton(onPressed: widget.onRetry, child: const Text('다시 시도')),
            ],
          ),
        ),
    };
  }
}
