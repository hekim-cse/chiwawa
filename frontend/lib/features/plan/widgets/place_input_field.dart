import 'package:flutter/material.dart';

import '../../../app/theme.dart';

class PlaceInputField extends StatefulWidget {
  const PlaceInputField({
    required this.places,
    required this.onAdd,
    required this.onRemove,
    super.key,
  });

  final List<String> places;
  final ValueChanged<String> onAdd;
  final ValueChanged<String> onRemove;

  @override
  State<PlaceInputField> createState() => _PlaceInputFieldState();
}

class _PlaceInputFieldState extends State<PlaceInputField> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    widget.onAdd(text);
    _controller.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ChiwawaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _controller,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _submit(),
            decoration: InputDecoration(
              hintText: '장소를 검색하거나 직접 입력',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(
                onPressed: _submit,
                icon: const Icon(Icons.add_circle),
                color: ChiwawaColors.primary,
              ),
              filled: true,
              fillColor: ChiwawaColors.background,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final place in widget.places)
                InputChip(
                  label: Text(place),
                  selected: true,
                  selectedColor: ChiwawaColors.secondary,
                  checkmarkColor: ChiwawaColors.primary,
                  deleteIconColor: ChiwawaColors.primary,
                  labelStyle: const TextStyle(
                    color: ChiwawaColors.primary,
                    fontWeight: FontWeight.w800,
                  ),
                  onDeleted: () => widget.onRemove(place),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
