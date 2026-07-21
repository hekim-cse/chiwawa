import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../core/models/travel_models.dart';
import '../../../shared/widgets/app_viewport.dart';

Future<PhotoSearchResult?> showPlaceCorrectionSheet(
  BuildContext context, {
  required PhotoSearchResult result,
}) {
  return showModalBottomSheet<PhotoSearchResult>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    constraints: const BoxConstraints(maxWidth: AppLayout.maxContentWidth),
    backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(
        top: Radius.circular(ChiwawaRadii.sheet),
      ),
    ),
    builder: (_) => _PlaceCorrectionSheet(result: result),
  );
}

class _PlaceCorrectionSheet extends StatefulWidget {
  const _PlaceCorrectionSheet({required this.result});

  final PhotoSearchResult result;

  @override
  State<_PlaceCorrectionSheet> createState() => _PlaceCorrectionSheetState();
}

class _PlaceCorrectionSheetState extends State<_PlaceCorrectionSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _addressController;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.result.name);
    _addressController = TextEditingController(text: widget.result.address);
  }

  @override
  void dispose() {
    _nameController.dispose();
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
                      '장소 정보 수정',
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
              TextFormField(
                key: const ValueKey('place-correction-name'),
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: '장소 이름',
                  prefixIcon: Icon(Icons.place_outlined),
                ),
                validator: (value) => value == null || value.trim().isEmpty
                    ? '장소 이름을 입력해 주세요.'
                    : null,
              ),
              const SizedBox(height: ChiwawaSpacing.sm),
              TextFormField(
                key: const ValueKey('place-correction-address'),
                controller: _addressController,
                minLines: 1,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: '주소',
                  prefixIcon: Icon(Icons.map_outlined),
                ),
              ),
              const SizedBox(height: ChiwawaSpacing.lg),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  key: const ValueKey('save-place-correction'),
                  onPressed: _submit,
                  icon: const Icon(Icons.check_rounded),
                  label: const Text('수정 완료'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    Navigator.pop(
      context,
      widget.result.copyWith(
        name: _nameController.text.trim(),
        address: _addressController.text.trim(),
      ),
    );
  }
}
