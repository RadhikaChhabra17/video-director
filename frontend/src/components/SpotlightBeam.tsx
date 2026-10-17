import React, { useEffect, useRef } from 'react';

interface SpotlightBeamProps {
  pageRef: React.RefObject<HTMLDivElement | null>;
  buttonRefs: React.RefObject<(HTMLButtonElement | null)[]>;
  activeFocalIndex: number;
  colorRgb: string; // e.g. "245, 158, 11"
  colorHex: string; // e.g. "#f59e0b"
}

interface Particle {
  t: number;          // 0 (at source emitter at top of page) to 1 (at target button)
  uRatio: number;     // 0 (left edge of beam) to 1 (right edge of beam)
  radius: number;
  speed: number;
  swaySpeed: number;
  swayAmp: number;
  phase: number;
  baseAlpha: number;
  twinkleSpeed: number;
  isBokeh: boolean;
}

export const SpotlightBeam: React.FC<SpotlightBeamProps> = ({
  pageRef,
  buttonRefs,
  activeFocalIndex,
  colorRgb,
  colorHex,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fixtureRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const page = pageRef.current;
    if (!canvas || !page) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let width = 0;
    let height = 0;

    const resizeCanvas = () => {
      if (!page || !canvas) return;
      const rect = page.getBoundingClientRect();
      width = canvas.width = rect.width;
      height = canvas.height = rect.height;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Initialize 48 dynamic floating dust motes & bokeh particles across full-page beam
    const particleCount = 48;
    const particles: Particle[] = [];

    for (let i = 0; i < particleCount; i++) {
      const isBokeh = Math.random() < 0.28;
      particles.push({
        t: Math.random(),
        uRatio: 0.12 + Math.random() * 0.76,
        radius: isBokeh ? 3.5 + Math.random() * 5.0 : 0.8 + Math.random() * 1.8,
        speed: 0.0012 + Math.random() * 0.0022,
        swaySpeed: 0.001 + Math.random() * 0.0018,
        swayAmp: 0.03 + Math.random() * 0.06,
        phase: Math.random() * Math.PI * 2,
        baseAlpha: isBokeh ? 0.22 + Math.random() * 0.28 : 0.45 + Math.random() * 0.5,
        twinkleSpeed: 0.002 + Math.random() * 0.004,
        isBokeh,
      });
    }

    // Striated god-ray shafts (theatrical volumetric beam slices)
    const rayRatios = [0.1, 0.22, 0.36, 0.5, 0.64, 0.78, 0.9];

    // Smooth physics interpolation for target button bounds
    let currentLeft = width * 0.2;
    let currentRight = width * 0.4;
    let currentTop = height * 0.85;
    let isInitialized = false;

    let startTime = performance.now();

    const render = (time: number) => {
      if (!canvas || !page) return;
      ctx.clearRect(0, 0, width, height);
      const elapsed = time - startTime;

      // 1. Single source emitter at the top ceiling of the page
      const sourceX = width / 2;
      const sourceY = 14;
      const sourceHalfWidth = 32;

      // Measure active target button relative to full page
      const pageRect = page.getBoundingClientRect();
      const targetBtn = buttonRefs.current ? buttonRefs.current[activeFocalIndex] : null;

      let destLeft = width * 0.2;
      let destRight = width * 0.4;
      let destTop = height * 0.85;

      if (targetBtn) {
        const btnRect = targetBtn.getBoundingClientRect();
        destLeft = btnRect.left - pageRect.left;
        destRight = btnRect.right - pageRect.left;
        destTop = btnRect.top - pageRect.top;
      }

      if (!isInitialized) {
        currentLeft = destLeft;
        currentRight = destRight;
        currentTop = destTop;
        isInitialized = true;
      } else {
        // Smooth responsive interpolation when category changes
        const ease = 0.12;
        currentLeft += (destLeft - currentLeft) * ease;
        currentRight += (destRight - currentRight) * ease;
        currentTop += (destTop - currentTop) * ease;
      }

      const targetCenterX = (currentLeft + currentRight) / 2;
      const targetWidth = Math.max(20, currentRight - currentLeft);

      // Compute spotlight directional angle from top of page
      const deltaX = targetCenterX - sourceX;
      const deltaY = currentTop - sourceY;
      const swivelAngleRad = Math.atan2(deltaX, deltaY);
      const swivelAngleDeg = (swivelAngleRad * 180) / Math.PI;

      // Update rotating ceiling stage light fixture
      if (fixtureRef.current) {
        fixtureRef.current.style.transform = `translate(-50%, 0) rotate(${swivelAngleDeg}deg)`;
      }

      // 2. VOLUMETRIC CONE OF LIGHT FROM TOP OF PAGE
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(sourceX - sourceHalfWidth, sourceY);
      ctx.lineTo(sourceX + sourceHalfWidth, sourceY);
      ctx.lineTo(currentRight + 8, currentTop + 4);
      ctx.lineTo(currentLeft - 8, currentTop + 4);
      ctx.closePath();

      // Full-length volumetric linear gradient along beam direction
      const coneGrad = ctx.createLinearGradient(sourceX, sourceY, targetCenterX, currentTop);
      coneGrad.addColorStop(0, `rgba(255, 255, 255, 0.72)`);
      coneGrad.addColorStop(0.06, `rgba(${colorRgb}, 0.48)`);
      coneGrad.addColorStop(0.22, `rgba(${colorRgb}, 0.26)`);
      coneGrad.addColorStop(0.55, `rgba(${colorRgb}, 0.16)`);
      coneGrad.addColorStop(0.85, `rgba(${colorRgb}, 0.08)`);
      coneGrad.addColorStop(1, `rgba(${colorRgb}, 0.02)`);

      ctx.fillStyle = coneGrad;
      ctx.fill();

      // 3. STRIATED VOLUMETRIC GOD RAYS (Cinematic theatrical haze)
      ctx.clip(); // Keep striated rays within volumetric cone
      ctx.globalCompositeOperation = 'screen';

      for (let i = 0; i < rayRatios.length; i++) {
        const rRatio = rayRatios[i];
        const topX = sourceX - sourceHalfWidth + rRatio * (sourceHalfWidth * 2);
        const botX = currentLeft + rRatio * targetWidth;
        const rayWidth = 10 + (i % 3) * 8;

        ctx.beginPath();
        ctx.moveTo(topX - rayWidth * 0.35, sourceY);
        ctx.lineTo(topX + rayWidth * 0.35, sourceY);
        ctx.lineTo(botX + rayWidth * 0.85, currentTop);
        ctx.lineTo(botX - rayWidth * 0.85, currentTop);
        ctx.closePath();

        const rayGrad = ctx.createLinearGradient(topX, sourceY, botX, currentTop);
        const rayAlpha = 0.05 + 0.035 * Math.sin(elapsed * 0.0012 + i * 1.3);
        rayGrad.addColorStop(0, `rgba(255, 255, 255, ${rayAlpha * 1.6})`);
        rayGrad.addColorStop(0.25, `rgba(${colorRgb}, ${rayAlpha * 1.1})`);
        rayGrad.addColorStop(0.8, `rgba(${colorRgb}, ${rayAlpha * 0.5})`);
        rayGrad.addColorStop(1, `rgba(${colorRgb}, 0)`);

        ctx.fillStyle = rayGrad;
        ctx.fill();
      }

      ctx.restore();

      // 4. GROUND ILLUMINATION POOL (Bathing the selected category card)
      ctx.save();
      ctx.beginPath();
      const poolRadiusX = targetWidth * 0.55;
      const poolRadiusY = 12;
      ctx.ellipse(targetCenterX, currentTop + 2, poolRadiusX, poolRadiusY, 0, 0, Math.PI * 2);

      const poolGrad = ctx.createRadialGradient(
        targetCenterX,
        currentTop + 2,
        0,
        targetCenterX,
        currentTop + 2,
        poolRadiusX
      );
      poolGrad.addColorStop(0, `rgba(255, 255, 255, 0.8)`);
      poolGrad.addColorStop(0.35, `rgba(${colorRgb}, 0.5)`);
      poolGrad.addColorStop(0.75, `rgba(${colorRgb}, 0.16)`);
      poolGrad.addColorStop(1, `rgba(${colorRgb}, 0)`);

      ctx.fillStyle = poolGrad;
      ctx.fill();
      ctx.restore();

      // 5. DYNAMIC FLOATING DUST MOTES & GLOWING BOKEH PARTICLES ACROSS PAGE
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Drift upward from target toward ceiling source
        p.t -= p.speed;
        if (p.t < 0.02) {
          p.t = 0.98;
          p.uRatio = 0.12 + Math.random() * 0.76;
        }

        // Horizontal harmonic sway
        const sway = Math.sin(elapsed * p.swaySpeed + p.phase) * p.swayAmp;
        const currentU = Math.max(0.08, Math.min(0.92, p.uRatio + sway));

        // Compute particle position within the full-page angled cone trapezoid
        const yPos = sourceY + p.t * (currentTop - sourceY);
        const leftEdgeAtT = (sourceX - sourceHalfWidth) + p.t * (currentLeft - (sourceX - sourceHalfWidth));
        const rightEdgeAtT = (sourceX + sourceHalfWidth) + p.t * (currentRight - (sourceX + sourceHalfWidth));
        const xPos = leftEdgeAtT + currentU * (rightEdgeAtT - leftEdgeAtT);

        // Alpha twinkle & subtle edge fade
        const edgeFade = Math.sin(p.t * Math.PI);
        const twinkle = 0.75 + 0.25 * Math.sin(elapsed * p.twinkleSpeed + p.phase);
        const alpha = Math.max(0, Math.min(1, p.baseAlpha * edgeFade * twinkle));

        ctx.save();
        ctx.beginPath();
        ctx.arc(xPos, yPos, p.radius, 0, Math.PI * 2);

        if (p.isBokeh) {
          // Soft out-of-focus glowing bokeh disc
          const bGrad = ctx.createRadialGradient(xPos, yPos, 0, xPos, yPos, p.radius);
          bGrad.addColorStop(0, `rgba(${colorRgb}, ${alpha * 0.9})`);
          bGrad.addColorStop(0.6, `rgba(${colorRgb}, ${alpha * 0.35})`);
          bGrad.addColorStop(1, `rgba(${colorRgb}, 0)`);
          ctx.fillStyle = bGrad;
        } else {
          // Sharp sparkling dust mote with high core brightness
          ctx.fillStyle = `rgba(255, 255, 255, ${alpha * 0.95})`;
          ctx.shadowColor = colorHex;
          ctx.shadowBlur = 8;
        }

        ctx.fill();
        ctx.restore();
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, [activeFocalIndex, colorRgb, colorHex, pageRef, buttonRefs]);

  return (
    <div
      className="pointer-events-none absolute inset-0 w-full h-full select-none overflow-hidden z-10"
      style={{
        filter: `drop-shadow(0 0 35px rgba(${colorRgb}, 0.25))`,
      }}
    >
      {/* 1. SINGLE OVERHEAD STAGE FIXTURE AT THE VERY TOP OF THE PAGE */}
      <div
        ref={fixtureRef}
        className="absolute left-1/2 top-0 z-30 transition-transform duration-75 ease-out origin-[50%_0%]"
      >
        {/* Ceiling mount mount bracket */}
        <div className="w-1.5 h-2.5 bg-white/30 mx-auto rounded-full" />

        {/* Outer metallic aperture collar */}
        <div
          className="w-24 sm:w-32 h-5 sm:h-6 rounded-[100%] border border-white/40 shadow-2xl relative flex items-center justify-center overflow-hidden"
          style={{
            background: 'radial-gradient(ellipse at center, rgba(22, 28, 42, 0.98) 0%, rgba(5, 7, 12, 1) 100%)',
            boxShadow: `0 0 25px rgba(0,0,0,0.95), 0 0 35px rgba(${colorRgb}, 0.5)`,
          }}
        >
          {/* Intense glowing white core emitter */}
          <div
            className="w-16 sm:w-22 h-2.5 sm:h-3 rounded-[100%] bg-white blur-[0.5px]"
            style={{
              boxShadow: `0 0 18px #ffffff, 0 0 40px rgba(${colorRgb}, 1), 0 0 75px rgba(${colorRgb}, 0.9)`,
            }}
          />
        </div>

        {/* Ambient lens flare corona at ceiling */}
        <div
          className="absolute -top-3 left-1/2 -translate-x-1/2 w-48 sm:w-64 h-14 sm:h-16 rounded-[100%] blur-[12px] pointer-events-none opacity-90"
          style={{
            background: `radial-gradient(ellipse at center, rgba(255, 255, 255, 0.95) 0%, rgba(${colorRgb}, 0.7) 40%, transparent 80%)`,
          }}
        />
      </div>

      {/* 2. DYNAMIC FULL-PAGE VOLUMETRIC BEAM & DUST MOTES CANVAS */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
      />
    </div>
  );
};
