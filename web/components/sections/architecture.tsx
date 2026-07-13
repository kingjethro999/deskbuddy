"use client";

import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import { BrainCircuit, AudioWaveform, MousePointerClick, AppWindow } from "lucide-react";
import { gsap, ScrollTrigger, prefersReducedMotion } from "@/lib/gsap";
import { SectionHeading } from "@/components/shared/section-heading";

const LAYERS = [
  {
    key: "brain",
    name: "BRAIN",
    icon: BrainCircuit,
    role: "The agent. A pluggable brain with native and Hermes backends.",
    examples: "native OpenAI-compatible loop, or shell out to the hermes CLI",
  },
  {
    key: "voice",
    name: "EARS + MOUTH",
    icon: AudioWaveform,
    role: "Speech in, speech out.",
    examples: "Whisper STT, piper / edge / espeak TTS",
  },
  {
    key: "hands",
    name: "HANDS",
    icon: MousePointerClick,
    role: "Actually drives your computer.",
    examples: "apps, shell, keyboard, mouse, files, screen",
  },
  {
    key: "face",
    name: "FACE",
    icon: AppWindow,
    role: "The window you see and talk to.",
    examples: "styled tkinter GUI now, Electron or Tauri later",
  },
] as const;

export function Architecture() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const section = sectionRef.current;
    if (!section) return;

    const ctx = gsap.context(() => {
      const cards = cardRefs.current.filter(Boolean) as HTMLDivElement[];
      gsap.from(cards, {
        opacity: 0,
        y: 40,
        stagger: 0.25,
        scrollTrigger: {
          trigger: section,
          start: "top 60%",
          end: "bottom 80%",
          scrub: 0.6,
        },
      });
      const lines = gsap.utils.toArray<SVGLineElement>(".arch-line");
      gsap.from(lines, {
        opacity: 0,
        scaleY: 0,
        transformOrigin: "top center",
        stagger: 0.2,
        scrollTrigger: {
          trigger: section,
          start: "top 50%",
          end: "center center",
          scrub: 0.8,
        },
      });
    }, section);

    return () => ctx.revert();
  }, []);

  return (
    <section ref={sectionRef} className="mx-auto max-w-5xl px-6 py-24">
      <SectionHeading
        eyebrow="Architecture"
        title="Four layers, cleanly separated."
        description="DeskBuddy is a voice and input skin over a pluggable brain. Each layer does one job, and the brain can be swapped without touching the rest."
      />
      <div className="relative mt-12 flex flex-col items-center gap-6">
        <svg
          className="absolute left-1/2 top-0 hidden h-full -translate-x-1/2 md:block"
          width="2"
          aria-hidden
        >
          {LAYERS.map((_, i) =>
            i < LAYERS.length - 1 ? (
              <line
                key={i}
                className="arch-line"
                x1="1"
                y1={`${(i + 0.5) * (100 / LAYERS.length)}%`}
                x2="1"
                y2={`${(i + 1.5) * (100 / LAYERS.length)}%`}
                stroke="var(--color-border)"
                strokeWidth="2"
              />
            ) : null,
          )}
        </svg>

        {LAYERS.map((layer, i) => {
          const Icon = layer.icon;
          return (
            <motion.div
              key={layer.key}
              ref={(el) => {
                cardRefs.current[i] = el;
              }}
              className="relative z-10 w-full max-w-md rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raised)] p-6"
            >
              <div className="flex items-start gap-4">
                <div className="rounded-md bg-[var(--color-accent-dim)] p-3 text-[var(--color-accent)]">
                  <Icon className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{layer.name}</h3>
                  <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                    {layer.role}
                  </p>
                  <p className="mt-2 font-mono text-xs text-[var(--color-text-muted)]">
                    {layer.examples}
                  </p>
                </div>
              </div>
            </motion.div>
          );
        })}

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mt-4 rounded-md border border-dashed border-[var(--color-accent)] bg-[var(--color-surface)] px-5 py-3 text-center text-sm text-[var(--color-text-secondary)]"
        >
          Pluggable brain branches to <span className="text-[var(--color-accent)]">native</span> or{" "}
          <span className="text-[var(--color-accent)]">hermes</span>.
        </motion.div>
      </div>
    </section>
  );
}
