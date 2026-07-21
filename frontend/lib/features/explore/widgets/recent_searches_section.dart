import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../../../shared/widgets/async_value_view.dart';

class RecentSearchesSection extends StatelessWidget {
  const RecentSearchesSection({
    required this.value,
    required this.onRetry,
    required this.onSelected,
    super.key,
  });

  final AsyncValue<List<PhotoSearchResult>> value;
  final VoidCallback onRetry;
  final ValueChanged<PhotoSearchResult> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '최근 탐색',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 12),
        AsyncValueView<List<PhotoSearchResult>>(
          value: value,
          loadingHeight: 142,
          onRetry: onRetry,
          builder: (recentSearches) {
            if (recentSearches.isEmpty) {
              return const SizedBox(
                height: 96,
                child: Center(
                  child: Text(
                    '최근 탐색한 장소가 없어요.',
                    style: TextStyle(color: ChiwawaColors.textSecondary),
                  ),
                ),
              );
            }
            return SizedBox(
              height: 142,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: recentSearches.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, index) {
                  final item = recentSearches[index];
                  return _RecentSearchCard(
                    key: ValueKey(
                      'recent-search-${item.identityKey}-$index',
                    ),
                    item: item,
                    index: index,
                    onTap: () => onSelected(item),
                  );
                },
              ),
            );
          },
        ),
      ],
    );
  }
}

class _RecentSearchCard extends StatelessWidget {
  const _RecentSearchCard({
    required this.item,
    required this.index,
    required this.onTap,
    super.key,
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
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: index.isEven
                        ? const [Color(0xFFFFD7DF), Color(0xFFFFF1C7)]
                        : const [Color(0xFFFFE6EC), Color(0xFFEAF7FF)],
                  ),
                ),
                child: const SizedBox(
                  height: 86,
                  width: double.infinity,
                  child: Icon(
                    Icons.photo_camera_rounded,
                    color: ChiwawaColors.primary,
                    size: 30,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(10),
                child: Text(
                  item.name,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
