import 'package:echosphere/widgets/custom_widgets/custom_text.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class EchoSphereTextSpan {
  final String text;
  final TextVariant variant;
  final Color? color;
  final double? size;

  const EchoSphereTextSpan({
    required this.text,
    this.variant = TextVariant.regular,
    this.color,
    this.size,
  });
}

class EchoSphereTextSpans extends StatelessWidget {
  final List<EchoSphereTextSpan>? spans;
  final String? text;
  final TextAlign? textAlign;
  final TextOverflow? overflow;
  final int? maxLines;
  final double? fontSize;

  const EchoSphereTextSpans({
    super.key,
    this.spans,
    this.text,
    this.textAlign,
    this.overflow = TextOverflow.ellipsis,
    this.maxLines = 2,
    this.fontSize,
  }) : assert(spans != null || text != null,
            "Either 'spans' or 'text' must be provided.");

  TextStyle _getTextStyle(TextVariant variant, BuildContext context,
      {Color? color, double? size}) {
    final fontWeight = switch (variant) {
      TextVariant.semiBold => FontWeight.w600,
      TextVariant.bold => FontWeight.bold,
      TextVariant.regular => FontWeight.normal,
    };
    final effectiveSize = size ?? 14.0;
    return GoogleFonts.inter(
      fontWeight: fontWeight,
      fontSize: effectiveSize,
      color: color ?? Theme.of(context).textTheme.bodyMedium?.color,
      letterSpacing: -0.02 * effectiveSize,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (spans != null && spans!.isNotEmpty) {
      return RichText(
        textAlign: textAlign ?? TextAlign.start,
        maxLines: maxLines,
        overflow: overflow ?? TextOverflow.ellipsis,
        text: TextSpan(
          children: spans!.map((span) {
            return TextSpan(
              text: span.text,
              style: _getTextStyle(
                span.variant,
                context,
                color: span.color,
                size: fontSize,
              ),
            );
          }).toList(),
        ),
      );
    }

    return Text(
      text ?? "",
      textAlign: textAlign,
      overflow: overflow,
      maxLines: maxLines,
      style: _getTextStyle(TextVariant.regular, context),
    );
  }
}
