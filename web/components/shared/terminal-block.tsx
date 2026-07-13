"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export function TerminalBlock({
  code,
  className,
  label,
}: {
  code: string;
  className?: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Copy failed");
    }
  };

  return (
    <div
      className={cn(
        "group relative rounded-md border border-[var(--color-border)] bg-[var(--color-code-bg)]",
        className,
      )}
    >
      {label && (
        <div className="border-b border-[var(--color-border)] px-4 py-2 font-mono text-xs text-[var(--color-text-muted)]">
          {label}
        </div>
      )}
      <button
        onClick={copy}
        aria-label="Copy command"
        className="absolute right-2 top-2 rounded p-1.5 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]"
      >
        {copied ? (
          <Check className="h-4 w-4 text-[var(--color-success)]" />
        ) : (
          <Copy className="h-4 w-4" />
        )}
      </button>
      <pre className="overflow-x-auto px-4 py-4 font-mono text-sm leading-relaxed text-[var(--color-text-primary)]">
        <code>{code}</code>
      </pre>
    </div>
  );
}
