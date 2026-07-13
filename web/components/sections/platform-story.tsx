"use client";

import { MonitorCheck, Radio, ShieldAlert, TerminalSquare, Apple } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { SectionHeading } from "@/components/shared/section-heading";

const PROVIDERS = [
  { os: "Linux X11", name: "X11Provider", needs: "xdotool / wmctrl", detail: "Full control on X11 sessions (or XWayland apps)." },
  { os: "Linux Wayland", name: "WaylandProvider", needs: "ydotool, /dev/uinput", detail: "Modern sessions. Needs uinput access for cross-window input." },
  { os: "Windows", name: "WindowsProvider", needs: "PowerShell (nircmd optional)", detail: "SendKeys for typing/keys, nircmd for clicks." },
  { os: "macOS", name: "MacProvider", needs: "osascript (cliclick optional)", detail: "AppleScript System Events for typing/keys, cliclick for clicks." },
];

export function PlatformStory() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-24">
      <SectionHeading
        eyebrow="Platform reality"
        title="Runs on Linux, Windows, and macOS."
        description="One input interface, four backends. DeskBuddy detects your OS and picks the right one at runtime. The brain and voice layers are identical everywhere. No paid SDK, no cloud required for any of it."
      />

      <Tabs defaultValue="wayland" className="mt-10">
        <TabsList>
          <TabsTrigger value="x11">Linux X11</TabsTrigger>
          <TabsTrigger value="wayland">Linux Wayland</TabsTrigger>
          <TabsTrigger value="windows">Windows</TabsTrigger>
          <TabsTrigger value="macos">macOS</TabsTrigger>
        </TabsList>

        <TabsContent value="x11">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
            <div className="flex items-center gap-3 text-[var(--color-accent)]">
              <MonitorCheck className="h-5 w-5" />
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Linux, X11 session</h3>
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
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Linux, Wayland session</h3>
            </div>
            <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
              Uses ydotool with /dev/uinput for cross-window input. The most common modern setup on Ubuntu.
            </p>
          </div>
        </TabsContent>

        <TabsContent value="windows">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
            <div className="flex items-center gap-3 text-[var(--color-accent)]">
              <TerminalSquare className="h-5 w-5" />
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Windows</h3>
            </div>
            <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
              Installs with the PowerShell one-liner. Uses PowerShell SendKeys for typing/keys; nircmd gives you clicks. Install via the same curl or iex command as everyone else.
            </p>
          </div>
        </TabsContent>

        <TabsContent value="macos">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
            <div className="flex items-center gap-3 text-[var(--color-accent)]">
              <Apple className="h-5 w-5" />
              <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">macOS</h3>
            </div>
            <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
              Installs with the curl one-liner. Uses AppleScript System Events for typing/keys; cliclick adds clicks. Same brain, same wake word, different input backend.
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
                <li key={p.os}>
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
