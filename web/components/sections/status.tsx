"use client";

import { motion } from "motion/react";
import { CheckCircle2, Circle } from "lucide-react";
import { SectionHeading } from "@/components/shared/section-heading";

const WORKING = [
  "Pluggable brain (native + hermes)",
  "8 PC-control tools (apps, shell, keyboard, mouse, files, screen)",
  "STT/TTS with graceful fallbacks",
  "Terminal setup wizard",
  "tkinter GUI",
  "Cross-platform installer (curl + PowerShell)",
];

const NEXT = [
  "Always-on wake word via openWakeWord",
  "Streaming STT with silence detection",
  "Screen-vision tool",
  "Richer GUI with waveform",
  "Packaging and distribution",
];

function List({ items, done }: { items: string[]; done: boolean }) {
  return (
    <motion.ul
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.3 }}
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: 0.08 } },
      }}
      className="space-y-3"
    >
      {items.map((item) => (
        <motion.li
          key={item}
          variants={{
            hidden: { opacity: 0, x: -12 },
            show: { opacity: 1, x: 0 },
          }}
          className="flex items-start gap-3 text-sm text-[var(--color-text-secondary)]"
        >
          {done ? (
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[var(--color-success)]" />
          ) : (
            <Circle className="mt-0.5 h-5 w-5 shrink-0 text-[var(--color-text-muted)]" />
          )}
          <span>{item}</span>
        </motion.li>
      ))}
    </motion.ul>
  );
}

export function Status() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-24">
      <SectionHeading
        eyebrow="Status"
        title="What works now, and what is next."
        description="A real project in active build. Here is the honest state."
      />
      <div className="mt-10 grid gap-8 md:grid-cols-2">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <h3 className="mb-4 text-lg font-semibold text-[var(--color-success)]">Working now</h3>
          <List items={WORKING} done />
        </div>
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
          <h3 className="mb-4 text-lg font-semibold text-[var(--color-accent-warm)]">Next</h3>
          <List items={NEXT} done={false} />
        </div>
      </div>
    </section>
  );
}
