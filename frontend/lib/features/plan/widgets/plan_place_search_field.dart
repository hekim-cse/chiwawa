import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/place_search_models.dart';
import '../plan_place_search_controller.dart';

class PlanPlaceSearchField extends StatefulWidget {
  const PlanPlaceSearchField({
    required this.day,
    required this.role,
    required this.searchState,
    required this.selectedPlace,
    required this.time,
    required this.onQueryChanged,
    required this.onPlaceSelected,
    required this.onRetry,
    required this.onTimePressed,
    super.key,
  });

  final int day;
  final PlanPlaceRole role;
  final PlanPlaceSearchState searchState;
  final PlaceSearchCandidate? selectedPlace;
  final String time;
  final ValueChanged<String> onQueryChanged;
  final ValueChanged<PlaceSearchCandidate> onPlaceSelected;
  final VoidCallback onRetry;
  final VoidCallback onTimePressed;

  @override
  State<PlanPlaceSearchField> createState() => _PlanPlaceSearchFieldState();
}

class _PlanPlaceSearchFieldState extends State<PlanPlaceSearchField> {
  late final TextEditingController _controller;

  String get _roleLabel => widget.role == PlanPlaceRole.start ? '출발' : '도착';

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.searchState.query);
  }

  @override
  void didUpdateWidget(covariant PlanPlaceSearchField oldWidget) {
    super.didUpdateWidget(oldWidget);
    final query = widget.searchState.query;
    if (_controller.text == query) return;
    _controller.value = _controller.value.copyWith(
      text: query,
      selection: TextSelection.collapsed(offset: query.length),
      composing: TextRange.empty,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final icon = widget.role == PlanPlaceRole.start
        ? Icons.trip_origin_rounded
        : Icons.location_on_rounded;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 32,
          height: 32,
          margin: const EdgeInsets.only(top: 8),
          decoration: const BoxDecoration(
            color: ChiwawaColors.secondary,
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 17, color: ChiwawaColors.primary),
        ),
        const SizedBox(width: ChiwawaSpacing.sm),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final stackTimeButton = constraints.maxWidth < 280;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (stackTimeButton) ...[
                    _buildSearchField(),
                    const SizedBox(height: ChiwawaSpacing.xs),
                    Align(
                      alignment: Alignment.centerRight,
                      child: _buildTimeButton(),
                    ),
                  ] else
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: _buildSearchField()),
                        const SizedBox(width: ChiwawaSpacing.xs),
                        _buildTimeButton(),
                      ],
                    ),
                  _buildSearchFeedback(context),
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildSearchField() {
    final selected = widget.selectedPlace != null &&
        widget.searchState.query == widget.selectedPlace!.name;
    return TextFormField(
      key: ValueKey(
        'plan-${widget.role.name}-place-${widget.day}',
      ),
      controller: _controller,
      onChanged: widget.onQueryChanged,
      textInputAction: TextInputAction.search,
      maxLines: 1,
      decoration: InputDecoration(
        labelText: '$_roleLabel 장소',
        hintText: '장소를 검색하세요',
        suffixIcon: Icon(
          selected ? Icons.check_circle_rounded : Icons.search_rounded,
          color: selected ? ChiwawaColors.success : ChiwawaColors.primary,
        ),
      ),
    );
  }

  Widget _buildTimeButton() {
    return SizedBox(
      width: 88,
      height: ChiwawaControlSizes.minimumInteractive,
      child: OutlinedButton(
        key: ValueKey(
          'plan-${widget.role.name}-time-${widget.day}',
        ),
        onPressed: widget.onTimePressed,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          foregroundColor: ChiwawaColors.primary,
          side: const BorderSide(color: ChiwawaColors.border),
        ),
        child: Text(
          widget.time,
          maxLines: 1,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
      ),
    );
  }

  Widget _buildSearchFeedback(BuildContext context) {
    final state = widget.searchState;
    final selectedPlace = widget.selectedPlace;
    if (selectedPlace != null && state.query == selectedPlace.name) {
      return _SelectedPlaceSummary(
        roleLabel: _roleLabel,
        place: selectedPlace,
      );
    }

    return switch (state.status) {
      PlanPlaceSearchStatus.idle => const SizedBox.shrink(),
      PlanPlaceSearchStatus.loading => const Padding(
          padding: EdgeInsets.only(top: ChiwawaSpacing.xs),
          child: Row(
            key: ValueKey('plan-place-search-loading'),
            children: [
              SizedBox.square(
                dimension: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              SizedBox(width: ChiwawaSpacing.xs),
              Text('장소를 검색하고 있어요.'),
            ],
          ),
        ),
      PlanPlaceSearchStatus.success => _PlaceSearchResults(
          day: widget.day,
          role: widget.role,
          results: state.results,
          onSelected: widget.onPlaceSelected,
        ),
      PlanPlaceSearchStatus.empty => const _SearchMessage(
          key: ValueKey('plan-place-search-empty'),
          icon: Icons.location_off_outlined,
          message: '검색 결과가 없어요. 장소 이름을 조금 더 자세히 입력해 주세요.',
        ),
      PlanPlaceSearchStatus.failure => _SearchMessage(
          key: const ValueKey('plan-place-search-failure'),
          icon: Icons.cloud_off_outlined,
          message: state.message ?? '장소를 검색하지 못했어요.',
          action: TextButton(
            key: ValueKey(
              'plan-${widget.role.name}-place-retry-${widget.day}',
            ),
            onPressed: widget.onRetry,
            child: const Text('다시 시도'),
          ),
        ),
    };
  }
}

class _SelectedPlaceSummary extends StatelessWidget {
  const _SelectedPlaceSummary({
    required this.roleLabel,
    required this.place,
  });

  final String roleLabel;
  final PlaceSearchCandidate place;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const ValueKey('plan-place-selected'),
      width: double.infinity,
      margin: const EdgeInsets.only(top: ChiwawaSpacing.xs),
      padding: const EdgeInsets.all(ChiwawaSpacing.sm),
      decoration: BoxDecoration(
        color: ChiwawaColors.movementSurface,
        borderRadius: BorderRadius.circular(ChiwawaRadii.control),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.verified_rounded,
            size: 18,
            color: ChiwawaColors.success,
          ),
          const SizedBox(width: ChiwawaSpacing.xs),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$roleLabel 장소 확정',
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: ChiwawaColors.success,
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  place.formattedAddress,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: ChiwawaColors.textSecondary,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PlaceSearchResults extends StatelessWidget {
  const _PlaceSearchResults({
    required this.day,
    required this.role,
    required this.results,
    required this.onSelected,
  });

  final int day;
  final PlanPlaceRole role;
  final List<PlaceSearchCandidate> results;
  final ValueChanged<PlaceSearchCandidate> onSelected;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: ValueKey('plan-${role.name}-place-results-$day'),
      width: double.infinity,
      margin: const EdgeInsets.only(top: ChiwawaSpacing.xs),
      decoration: BoxDecoration(
        color: ChiwawaColors.card,
        border: Border.all(color: ChiwawaColors.border),
        borderRadius: BorderRadius.circular(ChiwawaRadii.control),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          for (var index = 0; index < results.length; index++) ...[
            _PlaceSearchResultTile(
              day: day,
              role: role,
              place: results[index],
              onTap: () => onSelected(results[index]),
            ),
            if (index != results.length - 1)
              const Divider(height: 1, color: ChiwawaColors.border),
          ],
        ],
      ),
    );
  }
}

class _PlaceSearchResultTile extends StatelessWidget {
  const _PlaceSearchResultTile({
    required this.day,
    required this.role,
    required this.place,
    required this.onTap,
  });

  final int day;
  final PlanPlaceRole role;
  final PlaceSearchCandidate place;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '${place.name}, ${place.formattedAddress} 선택',
      child: InkWell(
        key: ValueKey(
          'plan-${role.name}-place-result-$day-${place.providerPlaceId}',
        ),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: ChiwawaSpacing.sm,
            vertical: ChiwawaSpacing.sm,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.place_outlined,
                size: 20,
                color: ChiwawaColors.primary,
              ),
              const SizedBox(width: ChiwawaSpacing.xs),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      place.name,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: ChiwawaColors.textPrimary,
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      place.formattedAddress,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: ChiwawaColors.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: ChiwawaSpacing.xs),
              const Icon(
                Icons.add_circle_outline_rounded,
                size: 21,
                color: ChiwawaColors.primary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SearchMessage extends StatelessWidget {
  const _SearchMessage({
    required this.icon,
    required this.message,
    this.action,
    super.key,
  });

  final IconData icon;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: ChiwawaSpacing.xs),
      padding: const EdgeInsets.all(ChiwawaSpacing.sm),
      decoration: BoxDecoration(
        color: ChiwawaColors.surfaceMuted,
        borderRadius: BorderRadius.circular(ChiwawaRadii.control),
      ),
      child: Row(
        children: [
          Icon(icon, size: 18, color: ChiwawaColors.primary),
          const SizedBox(width: ChiwawaSpacing.xs),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: ChiwawaColors.textSecondary,
                  ),
            ),
          ),
          if (action != null) action!,
        ],
      ),
    );
  }
}
