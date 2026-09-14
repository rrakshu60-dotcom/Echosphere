import 'package:echosphere/widgets/common/marquee_text.dart';
import 'package:auto_size_text/auto_size_text.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

enum TextVariant { regular, semiBold, bold }

class EchoSphereText extends StatelessWidget {
  final String text;
  final TextVariant variant;
  final Color? color;
  final double? size;
  final TextAlign? textAlign;
  final TextOverflow? overflow;
  final int? maxLines;
  final FontStyle fontStyle;
  final bool stripHtml;

  final bool autoResize;
  final double? minFontSize;
  final double? stepGranularity;
  final bool isMarquee;

  const EchoSphereText({
    super.key,
    required this.text,
    this.variant = TextVariant.regular,
    this.color,
    this.size,
    this.textAlign,
    this.overflow = TextOverflow.ellipsis,
    this.maxLines = 2,
    this.fontStyle = FontStyle.normal,
    this.stripHtml = false,
    this.autoResize = false,
    this.minFontSize = 10,
    this.stepGranularity = 1,
    this.isMarquee = false,
  });

  const EchoSphereText.regular({
    Key? key,
    required String text,
    Color? color,
    double? size,
    TextAlign? textAlign,
    TextOverflow? overflow = TextOverflow.ellipsis,
    int? maxLines = 2,
    FontStyle fontStyle = FontStyle.normal,
    bool stripHtml = false,
    bool autoResize = false,
    double? minFontSize = 10,
    double? stepGranularity = 1,
    bool isMarquee = false,
  }) : this(
          key: key,
          text: text,
          variant: TextVariant.regular,
          color: color,
          size: size,
          textAlign: textAlign,
          overflow: overflow,
          maxLines: maxLines,
          fontStyle: fontStyle,
          stripHtml: stripHtml,
          autoResize: autoResize,
          minFontSize: minFontSize,
          stepGranularity: stepGranularity,
          isMarquee: isMarquee,
        );

  const EchoSphereText.semiBold({
    Key? key,
    required String text,
    Color? color,
    double? size,
    TextAlign? textAlign,
    TextOverflow? overflow = TextOverflow.ellipsis,
    int? maxLines = 2,
    FontStyle fontStyle = FontStyle.normal,
    bool stripHtml = false,
    bool autoResize = false,
    double? minFontSize = 10,
    double? stepGranularity = 1,
    bool isMarquee = false,
  }) : this(
          key: key,
          text: text,
          variant: TextVariant.semiBold,
          color: color,
          size: size,
          textAlign: textAlign,
          overflow: overflow,
          maxLines: maxLines,
          fontStyle: fontStyle,
          stripHtml: stripHtml,
          autoResize: autoResize,
          minFontSize: minFontSize,
          stepGranularity: stepGranularity,
          isMarquee: isMarquee,
        );

  const EchoSphereText.bold({
    Key? key,
    required String text,
    Color? color,
    double? size,
    TextAlign? textAlign,
    TextOverflow? overflow = TextOverflow.ellipsis,
    int? maxLines = 2,
    FontStyle fontStyle = FontStyle.normal,
    bool stripHtml = false,
    bool autoResize = false,
    double? minFontSize = 10,
    double? stepGranularity = 1,
    bool isMarquee = false,
  }) : this(
          key: key,
          text: text,
          variant: TextVariant.bold,
          color: color,
          size: size,
          textAlign: textAlign,
          overflow: overflow,
          maxLines: maxLines,
          fontStyle: fontStyle,
          stripHtml: stripHtml,
          autoResize: autoResize,
          minFontSize: minFontSize,
          stepGranularity: stepGranularity,
          isMarquee: isMarquee,
        );

  @override
  Widget build(BuildContext context) {
    final fontWeight = switch (variant) {
      TextVariant.semiBold => FontWeight.w600,
      TextVariant.bold => FontWeight.bold,
      _ => FontWeight.normal,
    };

    final processedText = stripHtml ? _removeHtmlTags(text) : text;

    final effectiveSize = size ?? 14.0;
    final textStyle = GoogleFonts.inter(
      fontWeight: fontWeight,
      fontSize: effectiveSize,
      color: color,
      fontStyle: fontStyle,
      letterSpacing: -0.02 * effectiveSize,
    );

    final effectiveMaxLines = isMarquee ? 1 : maxLines;

    if (isMarquee) {
      return MarqueeText(
        processedText,
        style: textStyle,
        textAlign: textAlign,
        overflow: overflow,
        maxLines: effectiveMaxLines,
      );
    }

    if (!autoResize) {
      return Text(
        processedText,
        textAlign: textAlign,
        overflow: overflow,
        maxLines: effectiveMaxLines,
        style: textStyle,
      );
    }

    return AutoSizeText(
      processedText,
      textAlign: textAlign,
      maxLines: effectiveMaxLines,
      minFontSize: minFontSize ?? 10,
      stepGranularity: stepGranularity ?? 1,
      overflow: overflow,
      style: textStyle,
    );
  }

  String _removeHtmlTags(String input) {
    return input.replaceAll(RegExp(r"<[^>]*>"), "").trim();
  }
}
