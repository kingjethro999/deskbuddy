"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TerminalBlock } from "@/components/shared/terminal-block";
import { SectionHeading } from "@/components/shared/section-heading";

const GUI_STEPS = [
  { label: "install", code: 'curl -fsSL https://raw.githubusercontent.com/kingjethro999/deskbuddy/main/scripts/install.sh | bash' },
  { label: "windows", code: 'iex (irm https://raw.githubusercontent.com/kingjethro999/deskbuddy/main/scripts/install.ps1)' },
  { label: "setup", code: "buddy setup" },
  { label: "enroll", code: "buddy enroll" },
  { label: "launch", code: "buddy" },
];

const DEV_STEPS = [
  { label: "clone", code: "git clone https://github.com/kingjethro999/deskbuddy\ncd deskbuddy" },
  { label: "venv", code: "python3 -m venv .venv && .venv/bin/pip install -e ." },
  { label: "doctor", code: ".venv/bin/buddy doctor" },
  { label: "text loop", code: ".venv/bin/buddy --text" },
  { label: "voice", code: ".venv/bin/buddy --voice" },
  { label: "tests", code: "python -m pytest -q" },
];

export function QuickStart() {
  return (
    <section id="quick-start" className="mx-auto max-w-4xl px-6 py-24 scroll-mt-20">
      <SectionHeading
        eyebrow="Quick start"
        title="Up and running in minutes."
        description="Two paths. Pick the one that fits you. Both end at the same place: a voice buddy running your PC."
      />

      <Tabs defaultValue="gui" className="mt-10">
        <TabsList>
          <TabsTrigger value="gui">GUI only</TabsTrigger>
          <TabsTrigger value="dev">Developer / CLI</TabsTrigger>
        </TabsList>

        <TabsContent value="gui">
          <div className="space-y-4">
            {GUI_STEPS.map((s) => (
              <TerminalBlock key={s.label} label={s.label} code={s.code} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="dev">
          <div className="space-y-4">
            {DEV_STEPS.map((s) => (
              <TerminalBlock key={s.label} label={s.label} code={s.code} />
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </section>
  );
}
