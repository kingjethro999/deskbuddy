"use client";

import { useEffect, useRef } from "react";
import { gsap, ScrollTrigger, prefersReducedMotion } from "@/lib/gsap";
import { SectionHeading } from "@/components/shared/section-heading";
import { useReducedMotionSafe } from "@/hooks/use-reduced-motion-safe";

export function WakeWordDemo() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotionSafe();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const resize = () => {
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
    };
    resize();
    window.addEventListener("resize", resize);

    let active = false;
    let raf = 0;
    let t = 0;

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      const bars = 48;
      const gap = w / bars;
      const mid = h / 2;
      for (let i = 0; i < bars; i++) {
        const phase = i * 0.35;
        const noise = Math.sin(t * (active ? 0.18 : 0.06) + phase);
        const amp = (active ? 0.55 : 0.12) * (0.5 + 0.5 * Math.abs(noise));
        const barH = amp * h * 0.7;
        const x = i * gap + gap * 0.25;
        ctx.fillStyle = active
          ? "rgba(232,82,26,0.9)"
          : "rgba(74,179,212,0.5)";
        const r = Math.min(gap * 0.3, 6 * dpr);
        roundRect(ctx, x, mid - barH / 2, gap * 0.5, barH, r);
        ctx.fill();
      }
      t += 1;
      raf = requestAnimationFrame(draw);
    };

    const roundRect = (
      c: CanvasRenderingContext2D,
      x: number,
      y: number,
      ww: number,
      hh: number,
      r: number,
    ) => {
      c.beginPath();
      c.moveTo(x + r, y);
      c.arcTo(x + ww, y, x + ww, y + hh, r);
      c.arcTo(x + ww, y + hh, x, y + hh, r);
      c.arcTo(x, y + hh, x, y, r);
      c.arcTo(x, y, x + ww, y, r);
      c.closePath();
    };

    if (reduced) {
      active = true;
      draw();
      return () => {
        cancelAnimationFrame(raf);
        window.removeEventListener("resize", resize);
      };
    }

    draw();

    const st = ScrollTrigger.create({
      trigger: canvas,
      start: "top 70%",
      end: "bottom 30%",
      onToggle: (self) => {
        active = self.isActive;
        if (labelRef.current) {
          labelRef.current.textContent = self.isActive ? "buddy" : "listening";
        }
      },
    });

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      st.kill();
    };
  }, [reduced]);

  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <SectionHeading
        eyebrow="Wake word"
        title="Just say buddy."
        description="A custom engine built from scratch (MFCC features plus DTW template matching, numpy only) listens offline for your wake word. No paid SDK, no cloud. Here is what the listening state looks like."
      />
      <div className="mt-10 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
        <div className="mb-4 flex items-center gap-3">
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full rounded-full bg-[var(--color-accent-warm)] opacity-75 motion-safe:animate-ping" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-[var(--color-accent-warm)]" />
          </span>
          <span ref={labelRef} className="font-mono text-sm text-[var(--color-text-secondary)]">
            listening
          </span>
        </div>
        <canvas
          ref={canvasRef}
          className="h-32 w-full"
          aria-label="Waveform visualizer showing DeskBuddy in its listening state. This is an illustrative animation, not real microphone audio."
        />
      </div>
    </section>
  );
}
