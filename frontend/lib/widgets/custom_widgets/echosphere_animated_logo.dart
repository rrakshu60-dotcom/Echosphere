import 'dart:math' as math;
import 'package:anymex/models/logo_animation_type.dart';
import 'package:anymex/utils/theme_extensions.dart';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class EchoSphereAnimatedLogo extends StatefulWidget {
  final double size;
  final bool autoPlay;
  final VoidCallback? onAnimationComplete;
  final Color? color;
  final Gradient? gradient;
  final LogoAnimationType? forceAnimationType;

  const EchoSphereAnimatedLogo({
    super.key,
    this.size = 200,
    this.autoPlay = true,
    this.onAnimationComplete,
    this.color,
    this.gradient,
    this.forceAnimationType,
  });

  @override
  State<EchoSphereAnimatedLogo> createState() => _EchoSphereAnimatedLogoState();
}

class _EchoSphereAnimatedLogoState extends State<EchoSphereAnimatedLogo>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;
  late LogoAnimationType _animationType;

  @override
  void initState() {
    super.initState();
    _animationType = widget.forceAnimationType ?? _getStoredAnimationType();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    _animation = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: _getCurveForAnimationType(_animationType),
    ));

    if (widget.autoPlay) {
      _startAnimation();
    }
  }

  LogoAnimationType _getStoredAnimationType() {
    return LogoAnimationType.bottomToTop;
  }

  Curve _getCurveForAnimationType(LogoAnimationType type) {
    switch (type) {
      case LogoAnimationType.bottomToTop:
      case LogoAnimationType.wave:
        return Curves.easeInOut;
      case LogoAnimationType.fadeIn:
        return Curves.easeIn;
      case LogoAnimationType.scale:
        return Curves.elasticOut;
      case LogoAnimationType.rotate:
        return Curves.easeInOutCubic;
      case LogoAnimationType.slideRight:
        return Curves.easeOutCubic;
      case LogoAnimationType.pulse:
        return Curves.easeInOut;
      case LogoAnimationType.glitch:
        return Curves.easeInOutQuad;
      case LogoAnimationType.bounce:
        return Curves.bounceOut;
      case LogoAnimationType.spiral:
        return Curves.easeInOutQuart;
      case LogoAnimationType.particleConvergence:
        return Curves.easeInOutCubic;
      case LogoAnimationType.particleExplosion:
        return Curves.easeInOutCubic;
      case LogoAnimationType.orbitalRings:
        return Curves.easeInOutQuart;
      case LogoAnimationType.pixelAssembly:
        return Curves.easeOut;
      case LogoAnimationType.liquidMorph:
        return Curves.easeInOutSine;
      case LogoAnimationType.geometricUnfold:
        return Curves.easeInOutCubic;
      case LogoAnimationType.matrixRain:
        return Curves.easeInOut;
      case LogoAnimationType.shatter:
        return Curves.easeOutBack;
      case LogoAnimationType.hologram:
        return Curves.easeInOutCubic;
      case LogoAnimationType.vortex:
        return Curves.easeInOutQuart;
    }
  }

  Future<void> _startAnimation() async {
    await _controller.forward();
    widget.onAnimationComplete?.call();
  }

  void replay() {
    _controller.reset();
    _startAnimation();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: widget.size,
      height: widget.size,
      child: AnimatedBuilder(
        animation: _animation,
        builder: (context, child) {
          // Don't show anything during initial delay
          if (_animation.value < 0.05) {
            return const SizedBox.shrink();
          }
          return _buildAnimatedLogo();
        },
      ),
    );
  }

  Widget _buildAnimatedLogo() {
    switch (_animationType) {
      case LogoAnimationType.bottomToTop:
        return _buildBottomToTopLogo();
      case LogoAnimationType.fadeIn:
        return _buildFadeInLogo();
      case LogoAnimationType.scale:
        return _buildScaleLogo();
      case LogoAnimationType.rotate:
        return _buildRotateLogo();
      case LogoAnimationType.slideRight:
        return _buildSlideRightLogo();
      case LogoAnimationType.pulse:
        return _buildPulseLogo();
      case LogoAnimationType.glitch:
        return _buildGlitchLogo();
      case LogoAnimationType.bounce:
        return _buildBounceLogo();
      case LogoAnimationType.wave:
        return _buildWaveLogo();
      case LogoAnimationType.spiral:
        return _buildSpiralLogo();
      case LogoAnimationType.particleConvergence:
        return _buildParticleConvergenceLogo();
      case LogoAnimationType.particleExplosion:
        return _buildParticleExplosionLogo();
      case LogoAnimationType.orbitalRings:
        return _buildOrbitalRingsLogo();
      case LogoAnimationType.pixelAssembly:
        return _buildPixelAssemblyLogo();
      case LogoAnimationType.liquidMorph:
        return _buildLiquidMorphLogo();
      case LogoAnimationType.geometricUnfold:
        return _buildGeometricUnfoldLogo();
      case LogoAnimationType.matrixRain:
        return _buildMatrixRainLogo();
      case LogoAnimationType.shatter:
        return _buildShatterLogo();
      case LogoAnimationType.hologram:
        return _buildHologramLogo();
      case LogoAnimationType.vortex:
        return _buildVortexLogo();
    }
  }

  // bottom to top
  Widget _buildBottomToTopLogo() {
    return ClipRect(
      child: _buildBaseLogo(_animation.value * 100),
    );
  }

  // fade in
  Widget _buildFadeInLogo() {
    final scale = 0.95 + (_animation.value * 0.05);
    return Transform.scale(
      scale: scale,
      child: Opacity(
        opacity: _animation.value,
        child: _buildBaseLogo(100),
      ),
    );
  }

  // scale
  Widget _buildScaleLogo() {
    return Transform.scale(
      scale: _animation.value,
      child: Opacity(
        opacity: _animation.value.clamp(0.0, 1.0),
        child: _buildBaseLogo(100),
      ),
    );
  }

  // rotation
  Widget _buildRotateLogo() {
    final rotationAngle = (1 - _animation.value) * math.pi * 1.5;
    return Transform(
      alignment: Alignment.center,
      transform: Matrix4.identity()
        ..setEntry(3, 2, 0.002)
        ..rotateY(rotationAngle),
      child: Opacity(
        opacity: _animation.value,
        child: _buildBaseLogo(100),
      ),
    );
  }

  // horizontal slide
  Widget _buildSlideRightLogo() {
    final slideValue = Curves.easeOutCubic.transform(_animation.value);
    return Transform.translate(
      offset: Offset((1 - slideValue) * -widget.size * 1.2, 0),
      child: Opacity(
        opacity: _animation.value.clamp(0.0, 1.0),
        child: _buildBaseLogo(100),
      ),
    );
  }

  // pulse
  Widget _buildPulseLogo() {
    final pulseScale = 0.85 +
        (math.sin(_animation.value * math.pi * 3) * 0.08) +
        (_animation.value * 0.15);
    final glowIntensity = math.sin(_animation.value * math.pi * 2) * 0.3;

    return Stack(
      alignment: Alignment.center,
      children: [
        if (glowIntensity > 0)
          Opacity(
            opacity: glowIntensity,
            child: Transform.scale(
              scale: pulseScale * 1.15,
              child: _buildBaseLogo(100),
            ),
          ),
        Transform.scale(
          scale: pulseScale,
          child: Opacity(
            opacity: _animation.value.clamp(0.0, 1.0),
            child: _buildBaseLogo(100),
          ),
        ),
      ],
    );
  }

  // glitch
  Widget _buildGlitchLogo() {
    final phase = (_animation.value * 5) % 1.0;
    final glitchActive = phase > 0.85;
    final glitchOffset =
        glitchActive ? (math.Random().nextDouble() - 0.5) * 8 : 0.0;

    return Stack(
      alignment: Alignment.center,
      children: [
        if (glitchActive)
          Transform.translate(
            offset: Offset(-glitchOffset * 1.5, glitchOffset * 0.5),
            child: Opacity(
              opacity: 0.4,
              child: ColorFiltered(
                colorFilter: ColorFilter.mode(
                  Colors.cyan.opaque(0.7, iReallyMeanIt: true),
                  BlendMode.modulate,
                ),
                child: _buildBaseLogo(100),
              ),
            ),
          ),
        if (glitchActive)
          Transform.translate(
            offset: Offset(glitchOffset * 1.5, -glitchOffset * 0.5),
            child: Opacity(
              opacity: 0.4,
              child: ColorFiltered(
                colorFilter: ColorFilter.mode(
                  Colors.red.opaque(0.7, iReallyMeanIt: true),
                  BlendMode.modulate,
                ),
                child: _buildBaseLogo(100),
              ),
            ),
          ),
        Transform.translate(
          offset: Offset(glitchOffset * 0.3, 0),
          child: Opacity(
            opacity: _animation.value.clamp(0.0, 1.0),
            child: _buildBaseLogo(100),
          ),
        ),
      ],
    );
  }

  // bounce
  Widget _buildBounceLogo() {
    final bounceProgress = Curves.bounceOut.transform(_animation.value);
    return Transform.translate(
      offset: Offset(0, (1 - bounceProgress) * -widget.size * 0.6),
      child: Opacity(
        opacity: _animation.value.clamp(0.0, 1.0),
        child: _buildBaseLogo(100),
      ),
    );
  }

  // Professional wave animation with fluid motion
  Widget _buildWaveLogo() {
    final wavePhase = _animation.value * math.pi * 2;
    final waveAmplitude = (1 - _animation.value) * 12;
    final xOffset = math.sin(wavePhase) * waveAmplitude;
    final yOffset = math.cos(wavePhase * 1.5) * waveAmplitude * 0.5;

    return Transform.translate(
      offset: Offset(xOffset, yOffset),
      child: Transform.rotate(
        angle: math.sin(wavePhase) * 0.08,
        child: Opacity(
          opacity: _animation.value.clamp(0.0, 1.0),
          child: _buildBaseLogo(_animation.value * 100),
        ),
      ),
    );
  }

  // spiral
  Widget _buildSpiralLogo() {
    final spiralAngle = (1 - _animation.value) * math.pi * 3;
    final spiralScale = _animation.value * _animation.value;
    final distance = (1 - _animation.value) * widget.size * 0.3;

    return Transform.translate(
      offset: Offset(
        math.cos(spiralAngle) * distance,
        math.sin(spiralAngle) * distance,
      ),
      child: Transform.rotate(
        angle: spiralAngle,
        child: Transform.scale(
          scale: spiralScale,
          child: Opacity(
            opacity: _animation.value,
            child: _buildBaseLogo(100),
          ),
        ),
      ),
    );
  }

  // PARTICLE CONVERGENCE
  Widget _buildParticleConvergenceLogo() {
    // Adjust timing so animation starts after initial delay
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final particlePhase = adjustedProgress.clamp(0.0, 0.5) / 0.5;
    final convergePhase = (adjustedProgress - 0.4).clamp(0.0, 0.5) / 0.5;
    final logoPhase = (adjustedProgress - 0.7).clamp(0.0, 0.3) / 0.3;

    final particles = List.generate(16, (index) {
      final angle = (index / 16) * 2 * math.pi;
      final radius = widget.size * 0.5;
      final startX = math.cos(angle) * radius;
      final startY = math.sin(angle) * radius;

      final spiralFactor = math.sin(particlePhase * math.pi * 2 + index * 0.3);
      final moveX = startX + (math.cos(angle + spiralFactor) * 40);
      final moveY = startY + (math.sin(angle + spiralFactor) * 40);

      final currentX = convergePhase < 1.0 ? moveX * (1 - convergePhase) : 0.0;
      final currentY = convergePhase < 1.0 ? moveY * (1 - convergePhase) : 0.0;

      final colorPhase = (particlePhase + (index / 16)) % 1.0;
      final particleColor =
          HSVColor.fromAHSV(1.0, colorPhase * 360, 0.9, 1.0).toColor();
      final particleSize =
          10.0 + (math.sin(particlePhase * math.pi + index) * 4);
      final particleOpacity =
          convergePhase < 0.9 ? 1.0 : 1.0 - ((convergePhase - 0.9) / 0.1);

      return Positioned(
        left: widget.size / 2 + currentX - particleSize / 2,
        top: widget.size / 2 + currentY - particleSize / 2,
        child: Opacity(
          opacity: particleOpacity,
          child: Container(
            width: particleSize,
            height: particleSize,
            decoration: BoxDecoration(
              color: particleColor,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: particleColor.opaque(0.8, iReallyMeanIt: true),
                  blurRadius: 12,
                  spreadRadius: 3,
                ),
              ],
            ),
          ),
        ),
      );
    });

    return Stack(
      alignment: Alignment.center,
      children: [
        ...particles,
        if (logoPhase > 0)
          Transform.scale(
            scale: Curves.easeOutBack.transform(logoPhase),
            child: Opacity(
              opacity: logoPhase,
              child: _buildBaseLogo(logoPhase * 100),
            ),
          ),
      ],
    );
  }

  // PARTICLE EXPLOSION
  Widget _buildParticleExplosionLogo() {
    // Adjust timing
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final initialPhase = (adjustedProgress.clamp(0.0, 0.2) / 0.2);
    final explosionPhase = (adjustedProgress.clamp(0.2, 0.5) / 0.3);
    final reformPhase = (adjustedProgress - 0.5).clamp(0.0, 0.5) / 0.5;

    final logoOpacity = adjustedProgress < 0.2
        ? 1.0 - initialPhase
        : adjustedProgress > 0.6
            ? reformPhase
            : 0.0;
    final particles = List.generate(24, (index) {
      final angle = (index / 24) * 2 * math.pi;
      final speed = 0.8 + (math.Random(index).nextDouble() * 0.4);
      final distance = explosionPhase * widget.size * 0.9 * speed;
      final x = math.cos(angle) * distance * (1 - reformPhase);
      final y = math.sin(angle) * distance * (1 - reformPhase);

      final rotation = explosionPhase * math.pi * 6 * (1 - reformPhase);
      final particleOpacity =
          adjustedProgress > 0.15 && adjustedProgress < 0.85 ? 1.0 : 0.0;

      final colorIndex = (index / 24);
      final color =
          HSVColor.fromAHSV(1.0, colorIndex * 360, 0.95, 1.0).toColor();
      final particleSize = 8.0 + (index % 3) * 3.0;

      return Positioned(
        left: widget.size / 2 + x - particleSize / 2,
        top: widget.size / 2 + y - particleSize / 2,
        child: Transform.rotate(
          angle: rotation,
          child: Opacity(
            opacity: particleOpacity,
            child: Container(
              width: particleSize,
              height: particleSize,
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  colors: [color, color.opaque(0.6, iReallyMeanIt: true)],
                ),
                borderRadius: BorderRadius.circular(2),
                boxShadow: [
                  BoxShadow(
                    color: color.opaque(0.6, iReallyMeanIt: true),
                    blurRadius: 8,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    });

    return Stack(
      alignment: Alignment.center,
      children: [
        ...particles,
        if (logoOpacity > 0)
          Transform.scale(
            scale: Curves.easeOutBack.transform(logoOpacity),
            child: Opacity(
              opacity: logoOpacity,
              child: _buildBaseLogo(logoOpacity * 100),
            ),
          ),
      ],
    );
  }

  // ORBITAL RINGS
  Widget _buildOrbitalRingsLogo() {
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final ringPhase = adjustedProgress.clamp(0.0, 0.7) / 0.7;
    final logoPhase = (adjustedProgress - 0.5).clamp(0.0, 0.5) / 0.5;

    final rings = List.generate(5, (index) {
      final ringSize = widget.size * (0.3 + (index * 0.18));
      final rotationSpeed = (index % 2 == 0 ? 1 : -1) * (1 + index * 0.3);
      final rotation = ringPhase * math.pi * 2.5 * rotationSpeed;
      final scale = 1.2 - (ringPhase * (0.9 - index * 0.12));
      final opacity = (1.0 - ringPhase) * (1.0 - index * 0.15);

      final colors = [
        Colors.cyan,
        Colors.purple,
        Colors.pink,
        Colors.amber,
        Colors.teal,
      ];

      return Transform.rotate(
        angle: rotation,
        child: Opacity(
          opacity: opacity,
          child: Transform.scale(
            scale: scale,
            child: Container(
              width: ringSize,
              height: ringSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: colors[index],
                  width: 3.0 + (index * 0.5),
                ),
                boxShadow: [
                  BoxShadow(
                    color: colors[index].opaque(0.5, iReallyMeanIt: true),
                    blurRadius: 15,
                    spreadRadius: 3,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    });

    return Stack(
      alignment: Alignment.center,
      children: [
        ...rings,
        if (logoPhase > 0)
          Transform.scale(
            scale: Curves.easeOutBack.transform(logoPhase),
            child: Opacity(
              opacity: logoPhase,
              child: _buildBaseLogo(logoPhase * 100),
            ),
          ),
      ],
    );
  }

  // PIXEL ASSEMBLY
  Widget _buildPixelAssemblyLogo() {
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;
    final assemblyPhase = adjustedProgress;
    final logoPhase = (adjustedProgress - 0.7).clamp(0.0, 0.3) / 0.3;

    const gridSize = 10;
    final pixels = <Widget>[];

    for (int i = 0; i < gridSize; i++) {
      for (int j = 0; j < gridSize; j++) {
        final pixelIndex = i * gridSize + j;
        const totalPixels = gridSize * gridSize;
        final random = math.Random(pixelIndex);
        final appearTime = (random.nextDouble() * 0.5) + 0.1;
        final pixelProgress =
            (assemblyPhase - appearTime).clamp(0.0, 0.3) / 0.3;

        if (pixelProgress > 0) {
          final pixelSize = widget.size / gridSize;
          final startAngle = random.nextDouble() * math.pi * 2;
          final startDistance = random.nextDouble() * widget.size * 1.5;
          final startX = math.cos(startAngle) * startDistance;
          final startY = math.sin(startAngle) * startDistance;

          final currentX = startX * (1 - pixelProgress);
          final currentY = startY * (1 - pixelProgress);

          final colorValue = (pixelIndex / totalPixels);
          final color = HSVColor.fromAHSV(
            1.0,
            (colorValue * 360 + assemblyPhase * 60) % 360,
            0.8,
            0.95,
          ).toColor();

          pixels.add(
            Positioned(
              left: (i * pixelSize) + currentX,
              top: (j * pixelSize) + currentY,
              child: Transform.rotate(
                angle: (1 - pixelProgress) * math.pi * 2,
                child: Opacity(
                  opacity: pixelProgress,
                  child: Container(
                    width: pixelSize - 1.5,
                    height: pixelSize - 1.5,
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(2),
                      boxShadow: [
                        BoxShadow(
                          color: color.opaque(0.4, iReallyMeanIt: true),
                          blurRadius: 4,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          );
        }
      }
    }

    return Stack(
      alignment: Alignment.center,
      children: [
        if (assemblyPhase < 0.8)
          SizedBox(
            width: widget.size,
            height: widget.size,
            child: Stack(children: pixels),
          ),
        if (logoPhase > 0)
          Opacity(
            opacity: logoPhase,
            child: _buildBaseLogo(logoPhase * 100),
          ),
      ],
    );
  }

  // LIQUID MORPH
  Widget _buildLiquidMorphLogo() {
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final dropPhase = adjustedProgress.clamp(0.0, 0.4) / 0.4;
    final mergePhase = (adjustedProgress - 0.3).clamp(0.0, 0.5) / 0.5;
    final logoPhase = (adjustedProgress - 0.6).clamp(0.0, 0.4) / 0.4;

    final drops = List.generate(10, (index) {
      final angle = (index / 10) * 2 * math.pi;
      final radius = widget.size * 0.45;
      final startX = math.cos(angle) * radius;
      final startY = math.sin(angle) * radius - widget.size * 0.4;

      final gravity = dropPhase * dropPhase;
      final bounceHeight = startY + (widget.size * 0.4 * gravity);
      final elasticity =
          dropPhase > 0.8 ? math.sin((dropPhase - 0.8) * math.pi * 5) * 5 : 0.0;

      final currentX = startX * (1 - mergePhase);
      final currentY = (bounceHeight + elasticity) * (1 - mergePhase);

      final dropSize = 12.0 +
          (mergePhase * 15) +
          (math.sin(dropPhase * math.pi * 3 + index) * 3);
      final opacity = adjustedProgress < 0.75 ? 1.0 : 1.0 - logoPhase;

      final colors = [
        Colors.blue.shade400,
        Colors.cyan.shade400,
        Colors.teal.shade400,
        Colors.lightBlue.shade300,
        Colors.indigo.shade400,
        Colors.blue.shade600,
        Colors.cyan.shade600,
        Colors.teal.shade600,
        Colors.lightBlue.shade500,
        Colors.indigo.shade600,
      ];

      return Positioned(
        left: widget.size / 2 + currentX - dropSize / 2,
        top: widget.size / 2 + currentY - dropSize / 2,
        child: Opacity(
          opacity: opacity,
          child: Container(
            width: dropSize,
            height: dropSize,
            decoration: BoxDecoration(
              gradient: RadialGradient(
                colors: [
                  colors[index].opaque(0.9, iReallyMeanIt: true),
                  colors[index],
                ],
              ),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: colors[index].opaque(0.6, iReallyMeanIt: true),
                  blurRadius: 10,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),
        ),
      );
    });

    return Stack(
      alignment: Alignment.center,
      children: [
        ...drops,
        if (logoPhase > 0)
          Transform.scale(
            scale: Curves.easeOutBack.transform(logoPhase),
            child: Opacity(
              opacity: logoPhase,
              child: _buildBaseLogo(logoPhase * 100),
            ),
          ),
      ],
    );
  }

  // GEOMETRIC UNFOLD
  Widget _buildGeometricUnfoldLogo() {
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final unfoldPhase = adjustedProgress.clamp(0.0, 0.7) / 0.7;
    final logoPhase = (adjustedProgress - 0.5).clamp(0.0, 0.5) / 0.5;

    final shapes = List.generate(8, (index) {
      final angle = (index / 8) * 2 * math.pi;
      final distance = (1 - unfoldPhase) * widget.size * 0.6;
      final x = math.cos(angle) * distance;
      final y = math.sin(angle) * distance;

      final rotation = unfoldPhase * math.pi * 3 + (index * math.pi / 4);
      final scale = 1.2 - (unfoldPhase * 0.7);

      final shapeColors = [
        Colors.red.shade400,
        Colors.orange.shade400,
        Colors.amber.shade400,
        Colors.lime.shade400,
        Colors.green.shade400,
        Colors.cyan.shade400,
        Colors.blue.shade400,
        Colors.purple.shade400,
      ];

      Widget shape;
      final shapeType = index % 4;

      if (shapeType == 0) {
        shape = CustomPaint(
          size: const Size(45, 45),
          painter: _TrianglePainter(shapeColors[index]),
        );
      } else if (shapeType == 1) {
        shape = Container(
          width: 45,
          height: 45,
          decoration: BoxDecoration(
            color: shapeColors[index],
            borderRadius: BorderRadius.circular(8),
            boxShadow: [
              BoxShadow(
                color: shapeColors[index].opaque(0.6, iReallyMeanIt: true),
                blurRadius: 12,
                spreadRadius: 2,
              ),
            ],
          ),
        );
      } else if (shapeType == 2) {
        shape = Container(
          width: 45,
          height: 45,
          decoration: BoxDecoration(
            color: shapeColors[index],
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: shapeColors[index].opaque(0.6, iReallyMeanIt: true),
                blurRadius: 12,
                spreadRadius: 2,
              ),
            ],
          ),
        );
      } else {
        shape = Transform.rotate(
          angle: math.pi / 4,
          child: Container(
            width: 45,
            height: 45,
            decoration: BoxDecoration(
              color: shapeColors[index],
              borderRadius: BorderRadius.circular(4),
              boxShadow: [
                BoxShadow(
                  color: shapeColors[index].opaque(0.6, iReallyMeanIt: true),
                  blurRadius: 12,
                  spreadRadius: 2,
                ),
              ],
            ),
          ),
        );
      }

      return Positioned(
        left: widget.size / 2 + x - 22.5,
        top: widget.size / 2 + y - 22.5,
        child: Transform.rotate(
          angle: rotation,
          child: Transform.scale(
            scale: scale,
            child: Opacity(
              opacity: 1.0 - unfoldPhase,
              child: shape,
            ),
          ),
        ),
      );
    });

    return Stack(
      alignment: Alignment.center,
      children: [
        ...shapes,
        if (logoPhase > 0)
          Transform.scale(
            scale: Curves.easeOutBack.transform(logoPhase),
            child: Opacity(
              opacity: logoPhase,
              child: _buildBaseLogo(logoPhase * 100),
            ),
          ),
      ],
    );
  }

  // MATRIX RAIN
  Widget _buildMatrixRainLogo() {
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final rainPhase = adjustedProgress.clamp(0.0, 0.6) / 0.6;
    final formPhase = (adjustedProgress - 0.4).clamp(0.0, 0.6) / 0.6;
    final logoPhase = (adjustedProgress - 0.7).clamp(0.0, 0.3) / 0.3;

    const columns = 15;
    final rainDrops = List.generate(columns, (col) {
      final drops = <Widget>[];
      const dropsPerColumn = 8;

      for (int row = 0; row < dropsPerColumn; row++) {
        final random = math.Random(col * 100 + row);
        final dropDelay = random.nextDouble() * 0.3;
        final dropProgress = (rainPhase - dropDelay).clamp(0.0, 1.0);

        if (dropProgress > 0) {
          final x = (col / columns) * widget.size;
          final fallDistance = dropProgress * widget.size * 1.3;
          final y = -20.0 + fallDistance - (row * 25);

          final opacity =
              dropProgress < 0.8 ? 1.0 : 1.0 - ((dropProgress - 0.8) / 0.2);
          final fade = formPhase > 0 ? 1.0 - formPhase : 1.0;

          final brightness = 1.0 - (row / dropsPerColumn) * 0.6;

          drops.add(
            Positioned(
              left: x,
              top: y,
              child: Opacity(
                opacity: opacity * fade,
                child: Container(
                  width: widget.size / columns * 0.8,
                  height: 20,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.lightGreen
                            .opaque(brightness, iReallyMeanIt: true),
                        Colors.green
                            .opaque(brightness * 0.3, iReallyMeanIt: true),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(2),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.green
                            .opaque(0.5 * brightness, iReallyMeanIt: true),
                        blurRadius: 8,
                        spreadRadius: 1,
                      ),
                    ],
                  ),
                  child: Center(
                    child: Text(
                      String.fromCharCode(33 + random.nextInt(94)),
                      style: TextStyle(
                        color: Colors.white
                            .opaque(brightness, iReallyMeanIt: true),
                        fontSize: 12,
                        fontFamily: 'monospace',
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        }
      }
      return drops;
    }).expand((x) => x).toList();

    return Stack(
      alignment: Alignment.center,
      children: [
        if (formPhase < 1.0) ...rainDrops,
        if (logoPhase > 0)
          Transform.scale(
            scale: Curves.easeOutBack.transform(logoPhase),
            child: Opacity(
              opacity: logoPhase,
              child: _buildBaseLogo(logoPhase * 100),
            ),
          ),
      ],
    );
  }

  // SHATTER
  Widget _buildShatterLogo() {
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final shatterPhase = adjustedProgress.clamp(0.0, 0.5) / 0.5;
    final reformPhase = (adjustedProgress - 0.5).clamp(0.0, 0.5) / 0.5;

    final shards = List.generate(20, (index) {
      final angle = (index / 20) * 2 * math.pi;
      final random = math.Random(index);
      final distance =
          shatterPhase * widget.size * (0.6 + random.nextDouble() * 0.4);
      final x = math.cos(angle) * distance * (1 - reformPhase);
      final y = math.sin(angle) * distance * (1 - reformPhase);

      final rotation = shatterPhase *
          (random.nextDouble() * math.pi * 4 - math.pi * 2) *
          (1 - reformPhase);
      final scale = 0.3 + (shatterPhase * 0.7) * (1 - reformPhase * 0.5);

      final shardOpacity = adjustedProgress < 0.2
          ? 1.0 - (adjustedProgress / 0.2)
          : adjustedProgress > 0.8
              ? reformPhase
              : 0.8;

      final colors = [
        Colors.cyan.shade200,
        Colors.blue.shade200,
        Colors.lightBlue.shade200,
        Colors.teal.shade200,
      ];
      final color = colors[index % colors.length];

      return Positioned(
        left: widget.size / 2 + x - 25,
        top: widget.size / 2 + y - 25,
        child: Transform.rotate(
          angle: rotation,
          child: Transform.scale(
            scale: scale,
            child: Opacity(
              opacity: shardOpacity,
              child: Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      color,
                      color.opaque(0.3, iReallyMeanIt: true),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: Colors.white.opaque(0.5, iReallyMeanIt: true),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: color.opaque(0.4, iReallyMeanIt: true),
                      blurRadius: 10,
                      spreadRadius: 2,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    });

    final logoOpacity = adjustedProgress < 0.15
        ? 1.0 - (adjustedProgress / 0.15)
        : adjustedProgress > 0.7
            ? reformPhase
            : 0.0;

    return Stack(
      alignment: Alignment.center,
      children: [
        if (adjustedProgress > 0.1 && adjustedProgress < 0.9) ...shards,
        if (logoOpacity > 0)
          Transform.scale(
            scale: Curves.easeOutBack.transform(logoOpacity),
            child: Opacity(
              opacity: logoOpacity,
              child: _buildBaseLogo(logoOpacity * 100),
            ),
          ),
      ],
    );
  }

  // HOLOGRAM
  Widget _buildHologramLogo() {
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final scanPhase = adjustedProgress.clamp(0.0, 0.6) / 0.6;
    final stabilizePhase = (adjustedProgress - 0.5).clamp(0.0, 0.5) / 0.5;

    final flickerOffset = adjustedProgress < 0.7
        ? math.sin(adjustedProgress * math.pi * 30) * 2 * (1 - stabilizePhase)
        : 0.0;

    final scanLineY = -widget.size + (scanPhase * widget.size * 2);
    final glitchActive = adjustedProgress > 0.3 &&
        adjustedProgress < 0.6 &&
        ((adjustedProgress * 20) % 1.0) > 0.8;

    final logoOpacity = adjustedProgress.clamp(0.2, 0.9);
    final hologramColor = Colors.cyan.shade400;

    return Stack(
      alignment: Alignment.center,
      children: [
        if (scanPhase < 1.0)
          Positioned(
            top: scanLineY,
            child: Container(
              width: widget.size,
              height: 3,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.transparent,
                    hologramColor,
                    Colors.transparent,
                  ],
                ),
                boxShadow: [
                  BoxShadow(
                    color: hologramColor.opaque(0.8, iReallyMeanIt: true),
                    blurRadius: 15,
                    spreadRadius: 3,
                  ),
                ],
              ),
            ),
          ),
        if (glitchActive)
          Transform.translate(
            offset: Offset(flickerOffset * 3, 0),
            child: Opacity(
              opacity: 0.3,
              child: _buildBaseLogo(logoOpacity * 100),
            ),
          ),
        Transform.translate(
          offset: Offset(flickerOffset, 0),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Opacity(
                opacity: 0.4 * logoOpacity,
                child: Transform.scale(
                  scale: 1.1,
                  child: ColorFiltered(
                    colorFilter: ColorFilter.mode(
                      hologramColor,
                      BlendMode.srcATop,
                    ),
                    child: _buildBaseLogo(logoOpacity * 100),
                  ),
                ),
              ),
              Opacity(
                opacity: logoOpacity * 0.9,
                child: ColorFiltered(
                  colorFilter: ColorFilter.mode(
                    hologramColor.opaque(0.6, iReallyMeanIt: true),
                    BlendMode.modulate,
                  ),
                  child: _buildBaseLogo(logoOpacity * 100),
                ),
              ),
            ],
          ),
        ),
        ...List.generate(8, (index) {
          return Positioned(
            top: (index / 8) * widget.size,
            child: Opacity(
              opacity: 0.1 * logoOpacity,
              child: Container(
                width: widget.size,
                height: 1,
                color: Colors.cyan.shade100,
              ),
            ),
          );
        }),
      ],
    );
  }

  // VORTEX
  Widget _buildVortexLogo() {
    final adjustedProgress = (_animation.value - 0.05).clamp(0.0, 0.95) / 0.95;

    final vortexPhase = adjustedProgress.clamp(0.0, 0.7) / 0.7;
    final logoPhase = (adjustedProgress - 0.5).clamp(0.0, 0.5) / 0.5;

    final rings = List.generate(12, (index) {
      final progress = (vortexPhase - (index * 0.05)).clamp(0.0, 1.0);
      final ringSize = widget.size * (0.1 + index * 0.08) * progress;
      final depth = (1 - progress) * 0.8;
      final rotation = progress * math.pi * 6 + (index * math.pi / 6);

      final opacity = progress < 0.8
          ? (progress * 1.2).clamp(0.0, 1.0)
          : 1.0 - ((progress - 0.8) / 0.2);

      final zDepth = 1.0 - (depth * 0.5);

      final colors = [
        Colors.purple.shade400,
        Colors.deepPurple.shade400,
        Colors.indigo.shade400,
        Colors.blue.shade400,
      ];
      final color = colors[index % colors.length];

      return Transform.scale(
        scale: zDepth,
        child: Transform.rotate(
          angle: rotation,
          child: Opacity(
            opacity: opacity * (1 - logoPhase),
            child: Container(
              width: ringSize,
              height: ringSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: color,
                  width: 2.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: color.opaque(0.6, iReallyMeanIt: true),
                    blurRadius: 12 * zDepth,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    });

    return Stack(
      alignment: Alignment.center,
      children: [
        ...rings,
        if (logoPhase > 0)
          Transform.scale(
            scale: Curves.easeOutBack.transform(logoPhase),
            child: Transform(
              alignment: Alignment.center,
              transform: Matrix4.identity()
                ..setEntry(3, 2, 0.001)
                ..rotateX((1 - logoPhase) * math.pi * 0.5),
              child: Opacity(
                opacity: logoPhase,
                child: _buildBaseLogo(logoPhase * 100),
              ),
            ),
          ),
      ],
    );
  }

  static const String _echosphereBevelPath =
      'M 169.0 129.6 L 398.1 129.6 L 328.3 162.6 L 289.7 188.1 L 213.3 190.0 L 201.0 237.1 L 268.0 236.2 L 251.0 294.6 L 183.1 295.6 L 169.0 344.6 L 244.4 344.6 L 227.4 404.0 L 86.0 404.0 Z M 370.8 159.2 L 362.8 160.6 L 354.9 162.8 L 347.2 165.6 L 339.6 168.7 L 332.2 172.0 L 325.2 176.0 L 318.8 181.1 L 312.8 186.7 L 307.2 192.5 L 302.3 198.9 L 298.4 206.1 L 295.5 213.7 L 293.5 221.6 L 292.6 229.6 L 292.6 237.8 L 293.7 246.0 L 296.1 253.7 L 299.7 261.0 L 304.2 267.8 L 309.3 274.1 L 314.7 280.2 L 320.5 286.0 L 326.3 291.7 L 332.2 297.5 L 338.0 303.3 L 343.7 309.1 L 349.5 314.9 L 355.3 320.8 L 359.9 327.4 L 361.5 335.5 L 357.9 342.4 L 351.4 347.4 L 343.8 350.1 L 335.7 348.7 L 328.2 347.8 L 320.7 345.0 L 314.7 339.3 L 309.0 333.5 L 304.4 326.6 L 298.9 321.8 L 290.5 322.5 L 283.0 324.6 L 275.4 327.5 L 267.6 330.5 L 260.8 334.8 L 256.6 341.6 L 257.6 349.8 L 258.5 357.7 L 262.1 365.1 L 266.5 371.9 L 271.4 378.4 L 277.0 384.4 L 283.3 389.5 L 290.3 393.7 L 297.5 397.4 L 304.9 400.9 L 312.6 403.4 L 320.6 405.1 L 328.3 406.4 L 336.5 406.0 L 344.4 406.2 L 352.4 404.1 L 360.4 402.7 L 368.1 400.4 L 375.6 397.1 L 382.9 393.4 L 389.9 389.2 L 396.4 384.4 L 402.4 378.8 L 407.7 372.6 L 412.3 365.8 L 416.1 358.6 L 419.0 351.0 L 420.9 343.0 L 421.8 334.9 L 421.7 326.7 L 420.7 318.6 L 418.8 310.7 L 415.7 303.2 L 411.5 296.2 L 406.7 289.6 L 401.4 283.3 L 395.8 277.3 L 390.1 271.4 L 384.3 265.6 L 378.5 259.9 L 372.7 254.2 L 366.8 248.5 L 360.9 242.7 L 355.1 236.9 L 350.3 230.6 L 350.9 222.3 L 355.0 215.4 L 362.2 211.8 L 370.3 210.1 L 378.2 210.6 L 385.6 214.4 L 391.9 219.5 L 397.0 225.8 L 402.1 232.3 L 410.0 232.7 L 417.9 231.2 L 425.7 228.6 L 433.4 226.0 L 440.4 222.0 L 445.2 215.2 L 446.0 207.3 L 444.2 199.4 L 440.8 191.9 L 436.4 185.1 L 431.0 179.0 L 424.8 173.7 L 418.0 169.2 L 410.7 165.6 L 403.1 162.7 L 395.2 160.7 L 387.1 159.3 L 378.9 158.8 L 370.8 159.2 Z';

  static const String _echosphereFacesPath =
      'M 159.0 117.6 L 388.1 117.6 L 318.3 150.6 L 279.7 176.1 L 203.3 178.0 L 191.0 225.1 L 258.0 224.2 L 241.0 282.6 L 173.1 283.6 L 159.0 332.6 L 234.4 332.6 L 217.4 392.0 L 76.0 392.0 Z M 360.8 147.2 L 352.8 148.6 L 344.9 150.8 L 337.2 153.6 L 329.6 156.7 L 322.2 160.0 L 315.2 164.0 L 308.8 169.1 L 302.8 174.7 L 297.2 180.5 L 292.3 186.9 L 288.4 194.1 L 285.5 201.7 L 283.5 209.6 L 282.6 217.6 L 282.6 225.8 L 283.7 234.0 L 286.1 241.7 L 289.7 249.0 L 294.2 255.8 L 299.3 262.1 L 304.7 268.2 L 310.5 274.0 L 316.3 279.7 L 322.2 285.5 L 328.0 291.3 L 333.7 297.1 L 339.5 302.9 L 345.3 308.8 L 349.9 315.4 L 351.5 323.5 L 347.9 330.4 L 341.4 335.4 L 333.8 338.1 L 325.7 336.7 L 318.2 335.8 L 310.7 333.0 L 304.7 327.3 L 299.0 321.5 L 294.4 314.6 L 288.9 309.8 L 280.5 310.5 L 273.0 312.6 L 265.4 315.5 L 257.6 318.5 L 250.8 322.8 L 246.6 329.6 L 247.6 337.8 L 248.5 345.7 L 252.1 353.1 L 256.5 359.9 L 261.4 366.4 L 267.0 372.4 L 273.3 377.5 L 280.3 381.7 L 287.5 385.4 L 294.9 388.9 L 302.6 391.4 L 310.6 393.1 L 318.3 394.4 L 326.5 394.0 L 334.4 394.2 L 342.4 392.1 L 350.4 390.7 L 358.1 388.4 L 365.6 385.1 L 372.9 381.4 L 379.9 377.2 L 386.4 372.4 L 392.4 366.8 L 397.7 360.6 L 402.3 353.8 L 406.1 346.6 L 409.0 339.0 L 410.9 331.0 L 411.8 322.9 L 411.7 314.7 L 410.7 306.6 L 408.8 298.7 L 405.7 291.2 L 401.5 284.2 L 396.7 277.6 L 391.4 271.3 L 385.8 265.3 L 380.1 259.4 L 374.3 253.6 L 368.5 247.9 L 362.7 242.2 L 356.8 236.5 L 350.9 230.7 L 345.1 224.9 L 340.3 218.6 L 340.9 210.3 L 345.0 203.4 L 352.2 199.8 L 360.3 198.1 L 368.2 198.6 L 375.6 202.4 L 381.9 207.5 L 387.0 213.8 L 392.1 220.3 L 400.0 220.7 L 407.9 219.2 L 415.7 216.6 L 423.4 214.0 L 430.4 210.0 L 435.2 203.2 L 436.0 195.3 L 434.2 187.4 L 430.8 179.9 L 426.4 173.1 L 421.0 167.0 L 414.8 161.7 L 408.0 157.2 L 400.7 153.6 L 393.1 150.7 L 385.2 148.7 L 377.1 147.3 L 368.9 146.8 L 360.8 147.2 Z';

  Widget _buildBaseLogo(double fillHeight) {
    final theme = Theme.of(context);
    String fillGradientDef;

    if (widget.gradient != null) {
      final colors = widget.gradient is LinearGradient
          ? (widget.gradient as LinearGradient).colors
          : [theme.colorScheme.primary, theme.colorScheme.tertiary];

      fillGradientDef = _createFillGradient(colors, fillHeight);
    } else if (widget.color != null) {
      fillGradientDef =
          _createFillGradient([widget.color!, widget.color!], fillHeight);
    } else {
      fillGradientDef = _createFillGradient([
        const Color(0xFF5B68DF), // EchoSphere Royal Blue
        const Color(0xFF9D84E8), // EchoSphere Lilac / Lavender
        const Color(0xFFFFFFFF), // EchoSphere Gloss White
      ], fillHeight);
    }

    final logoSvg = '''
      <svg viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
        <defs>
          $fillGradientDef
          <linearGradient id="bevelGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#352B62" />
            <stop offset="100%" stop-color="#1A1535" />
          </linearGradient>
        </defs>
        <!-- 3D Bevel / Silhouette Base -->
        <path
          d="$_echosphereBevelPath"
          fill="url(#bevelGradient)"
          opacity="0.85"
        />
        <!-- Faint unlit base silhouette for depth -->
        <path
          d="$_echosphereFacesPath"
          fill="#1C1838"
          opacity="0.25"
        />
        <!-- Front Faces with Gradual Fill Gradient -->
        <path
          d="$_echosphereFacesPath"
          fill="url(#fillGradient)"
        />
      </svg>
    ''';

    return SvgPicture.string(
      logoSvg,
      width: widget.size,
      height: widget.size,
    );
  }

  String _createFillGradient(List<Color> colors, double fillHeight) {
    String gradientStops = '';
    for (int i = 0; i < colors.length; i++) {
      final offset = (i / (colors.length - 1)) * 100;
      gradientStops +=
          '<stop offset="$offset%" stop-color="${_colorToRgba(colors[i], 1.0)}" />';
    }

    return '''
      <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        $gradientStops
      </linearGradient>
      <linearGradient id="fillGradient" x1="0%" y1="100%" x2="0%" y2="0%">
        <stop offset="0%" stop-color="${_colorToRgba(colors[0], 1.0)}" />
        <stop offset="$fillHeight%" stop-color="${_colorToRgba(colors.last, 1.0)}" />
        <stop offset="$fillHeight%" stop-color="transparent" />
        <stop offset="100%" stop-color="transparent" />
      </linearGradient>
    ''';
  }

  String _colorToRgba(Color color, double opacity) {
    return 'rgba(${color.red}, ${color.green}, ${color.blue}, $opacity)';
  }
}

class _TrianglePainter extends CustomPainter {
  final Color color;
  _TrianglePainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    final path = Path()
      ..moveTo(size.width / 2, 0)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();

    canvas.drawPath(path, paint);
    canvas.drawShadow(path, color.opaque(0.5, iReallyMeanIt: true), 10.0, true);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
