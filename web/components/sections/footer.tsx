import { Code2 } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-10 sm:flex-row">
        <div className="text-center sm:text-left">
          <p className="font-display text-lg font-semibold text-[var(--color-text-primary)]">
            DeskBuddy
          </p>
          <p className="text-sm text-[var(--color-text-muted)]">
            Built by King Jethro Jerry.
          </p>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <a
            href="https://github.com/kingjethro999/deskbuddy"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-accent)]"
          >
            <Code2 className="h-4 w-4" /> GitHub
          </a>
          <span className="text-[var(--color-text-muted)]">
            Inspired by Hermes
          </span>
        </div>
      </div>
    </footer>
  );
}
