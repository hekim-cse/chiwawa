import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';

class TripListItem extends StatelessWidget {
  const TripListItem({
    required this.trip,
    required this.isCurrent,
    required this.onTap,
    super.key,
  });

  final Trip trip;
  final bool isCurrent;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final interestLabels = trip.interests
        .map((code) => TravelThemeLabel.fromCode(code).label)
        .join(' · ');

    return Material(
      color: isCurrent ? const Color(0xFFFFF1F4) : Colors.white,
      shape: RoundedRectangleBorder(
        side: BorderSide(
          color: isCurrent ? ChiwawaColors.primary : ChiwawaColors.border,
        ),
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: ValueKey('trip-card-${trip.id}'),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: isCurrent
                      ? ChiwawaColors.primary
                      : ChiwawaColors.secondary,
                  borderRadius: BorderRadius.circular(ChiwawaRadii.control),
                ),
                child: Icon(
                  Icons.luggage_rounded,
                  color: isCurrent ? Colors.white : ChiwawaColors.primary,
                  size: 22,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            trip.title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        if (isCurrent)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(
                                ChiwawaRadii.round,
                              ),
                            ),
                            child: const Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.check_circle_rounded,
                                  color: ChiwawaColors.primary,
                                  size: 14,
                                ),
                                SizedBox(width: 4),
                                Text(
                                  '현재',
                                  style: TextStyle(
                                    color: ChiwawaColors.primary,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${trip.city}, ${trip.country} · ${trip.travelers}명',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_displayDate(trip.startDate)} - ${_displayDate(trip.endDate)}',
                      style: const TextStyle(
                        color: ChiwawaColors.textSecondary,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (interestLabels.isNotEmpty) ...[
                      const SizedBox(height: 7),
                      Text(
                        '$interestLabels · ${trip.travelStyle.label}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: ChiwawaColors.primary,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _displayDate(String value) => value.replaceAll('-', '.');
