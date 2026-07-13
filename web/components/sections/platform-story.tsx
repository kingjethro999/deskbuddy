"use client";

import { MonitorCheck, Radio, ShieldAlert } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { SectionHeading } from "@/components/shared/section-heading";

const PROVIDERS = [
  {
    name: "X11Provider",
    needs: "xdotool / wmctrl",
    detail: "Full control. DeskBuddy injects input into any window on X11 sessions.",
  },
  {
    name: "WaylandProvider",
    needs: "ydotool, /dev/uinput",
    detail: "Modern sessions. Requires uinput access to inject input across windows.",
  },
  {
    name: "NullProvider",
    needs: "none",
    detail: "Explains the limitation and suggests logging into an Ubuntu on Xorg session for full control.",
  },
];

export function PlatformStory() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-24">
      <SectionHeading
        eyebrow="Platform reality"
        title="It actually reckons with Wayland."
        description="Wayland blocks apps from injecting input into other windows. DeskBuddy detects your session and picks the right provider at runtime. This is a real limitation, handled honestly, not hidden."
      />

      <Tabs defaultValue="wayland" className="mt-10">
        <TabsList>
          <TabsTrigger value="x11">X11</TabsTrigger>
          <TabsTrigger value="wayland">Wayland</TabsTrigger>
          <TabsTrigger value="neither">Undetected</TabsTrigger>
        </TabsList>

        <TabsContent value="x11">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
            <div className="flex items-center gap-3 text-[var(--color-accent)]">
              <MonitorCheck className="h-5 w-5" />
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">X11 session</h3>
            </div>
            <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
              Full hands-off control. DeskBuddy uses xdotool and wmctrl to drive any window.
            </p>
          </div>
        </TabsContent>

        <TabsContent value="wayland">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
            <div className="flex items-center gap-3 text-[var(--color-accent)]">
              <Radio className="h-5 w-5" />
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Wayland session</h3>
            </div>
            <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
              Uses ydotool with /dev/uinput for cross-window input. The most common modern setup on Ubuntu.
            </p>
          </div>
        </TabsContent>

        <TabsContent value="neither">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
            <div className="flex items-center gap-3 text-[var(--color-accent-warm)]">
              <ShieldAlert className="h-5 w-5" />
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">No session detected</h3>
            </div>
            <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
              DeskBuddy explains the limitation and suggests an Ubuntu on Xorg session for full control.
            </p>
          </div>
        </TabsContent>
      </Tabs>

      <Accordion type="single" collapsible className="mt-8">
        <AccordionItem value="providers">
          <AccordionTrigger>How does provider selection work?</AccordionTrigger>
          <AccordionContent>
            <ul className="space-y-3">
              {PROVIDERS.map((p) => (
                <li key={p.name}>
                  <span className="font-mono text-[var(--color-accent)]">{p.name}</span>
                  <span className="text-[var(--color-text-muted)]"> ({p.needs})</span>
                  <span className="block text-[var(--color-text-secondary)]">{p.detail}</span>
                </li>
              ))}
            </ul>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </section>
  );
}
