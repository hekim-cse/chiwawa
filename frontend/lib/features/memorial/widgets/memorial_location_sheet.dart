import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/memorial_models.dart';
import '../../../shared/widgets/app_viewport.dart';

class MemorialPhotoLocation {
  const MemorialPhotoLocation({
    required this.address,
    required this.latitude,
    required this.longitude,
  });

  final String address;
  final double latitude;
  final double longitude;
}

Future<MemorialPhotoLocation?> showMemorialLocationSheet(
  BuildContext context, {
  required MemorialPhoto photo,
}) {
  return showModalBottomSheet<MemorialPhotoLocation>(
    context: context,
    useSafeArea: true,
    isScrollControlled: true,
    constraints: const BoxConstraints(maxWidth: AppLayout.maxContentWidth),
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(
        top: Radius.circular(ChiwawaRadii.sheet),
      ),
    ),
    builder: (_) => _MemorialLocationSheet(photo: photo),
  );
}

class _MemorialLocationSheet extends StatefulWidget {
  const _MemorialLocationSheet({required this.photo});

  final MemorialPhoto photo;

  @override
  State<_MemorialLocationSheet> createState() => _MemorialLocationSheetState();
}

class _MemorialLocationSheetState extends State<_MemorialLocationSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _addressController;
  late final double _baseLatitude;
  late final double _baseLongitude;
  late double _latitude;
  late double _longitude;
  Offset _marker = const Offset(0.52, 0.48);

  @override
  void initState() {
    super.initState();
    _addressController = TextEditingController(text: widget.photo.address);
    _baseLatitude = widget.photo.latitude ?? 35.6812;
    _baseLongitude = widget.photo.longitude ?? 139.7671;
    _latitude = _baseLatitude;
    _longitude = _baseLongitude;
  }

  @override
  void dispose() {
    _addressController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(
          AppLayout.pageHorizontalPadding(context),
          ChiwawaSpacing.sm,
          AppLayout.pageHorizontalPadding(context),
          ChiwawaSpacing.xl,
        ),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: ChiwawaColors.textMuted,
                    borderRadius: BorderRadius.circular(ChiwawaRadii.round),
                  ),
                ),
              ),
              const SizedBox(height: ChiwawaSpacing.lg),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '사진 위치 수정',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  IconButton(
                    tooltip: '닫기',
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close_rounded),
                  ),
                ],
              ),
              const SizedBox(height: ChiwawaSpacing.md),
              _LocationCanvas(
                marker: _marker,
                onChanged: _updateMarker,
              ),
              const SizedBox(height: ChiwawaSpacing.md),
              TextFormField(
                key: const ValueKey('memorial-location-address'),
                controller: _addressController,
                decoration: const InputDecoration(
                  labelText: '위치 이름',
                  prefixIcon: Icon(Icons.place_outlined),
                ),
                validator: (value) => value == null || value.trim().isEmpty
                    ? '위치 이름을 입력해 주세요.'
                    : null,
              ),
              const SizedBox(height: ChiwawaSpacing.lg),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  key: const ValueKey('save-memorial-location'),
                  onPressed: _submit,
                  icon: const Icon(Icons.check_rounded),
                  label: const Text('위치 저장'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _updateMarker(Offset marker) {
    setState(() {
      final latitudeDelta = (0.5 - marker.dy) * 0.02;
      final longitudeDelta = (marker.dx - 0.5) * 0.02;
      _marker = marker;
      _latitude = _baseLatitude + latitudeDelta;
      _longitude = _baseLongitude + longitudeDelta;
    });
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    Navigator.pop(
      context,
      MemorialPhotoLocation(
        address: _addressController.text.trim(),
        latitude: _latitude,
        longitude: _longitude,
      ),
    );
  }
}

class _LocationCanvas extends StatelessWidget {
  const _LocationCanvas({required this.marker, required this.onChanged});

  final Offset marker;
  final ValueChanged<Offset> onChanged;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '사진 위치 지도',
      child: ClipRRect(
        borderRadius: BorderRadius.circular(ChiwawaRadii.card),
        child: AspectRatio(
          aspectRatio: 1.8,
          child: LayoutBuilder(
            builder: (context, constraints) {
              return GestureDetector(
                key: const ValueKey('memorial-location-map'),
                behavior: HitTestBehavior.opaque,
                onTapDown: (details) {
                  onChanged(
                    Offset(
                      (details.localPosition.dx / constraints.maxWidth)
                          .clamp(0.08, 0.92),
                      (details.localPosition.dy / constraints.maxHeight)
                          .clamp(0.12, 0.88),
                    ),
                  );
                },
                child: Stack(
                  children: [
                    const Positioned.fill(
                        child: CustomPaint(painter: _MapPainter())),
                    Positioned(
                      left: constraints.maxWidth * marker.dx - 20,
                      top: constraints.maxHeight * marker.dy - 38,
                      child: const Icon(
                        Icons.location_on_rounded,
                        size: 40,
                        color: ChiwawaColors.primary,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _MapPainter extends CustomPainter {
  const _MapPainter();

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = ChiwawaColors.mapLand);
    final water = Path()
      ..moveTo(size.width * 0.72, 0)
      ..quadraticBezierTo(
        size.width * 0.58,
        size.height * 0.48,
        size.width,
        size.height * 0.62,
      )
      ..lineTo(size.width, 0)
      ..close();
    canvas.drawPath(water, Paint()..color = ChiwawaColors.mapWater);
    final road = Paint()
      ..color = Colors.white
      ..strokeWidth = 5
      ..style = PaintingStyle.stroke;
    for (var index = 0; index < 4; index++) {
      final y = size.height * (0.2 + index * 0.2);
      canvas.drawLine(Offset(0, y), Offset(size.width, y - 18), road);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
