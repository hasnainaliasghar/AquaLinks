"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, ChevronUp, Map as MapIcon, Mountain, Satellite } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import type { Basemap } from "@/components/map/map";

const OPTIONS: { value: Basemap; label: string; icon: typeof MapIcon }[] = [
  { value: "street", label: "Street", icon: MapIcon },
  { value: "satellite", label: "Satellite", icon: Satellite },
  { value: "terrain", label: "Terrain", icon: Mountain },
];

export function BasemapSwitcher({
  value,
  onChange,
  className,
  defaultOpen = false,
}: {
  value: Basemap;
  onChange: (next: Basemap) => void;
  className?: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const reduce = useReducedMotion();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const active = OPTIONS.find((option) => option.value === value) ?? OPTIONS[0]!;
  const ActiveIcon = active.icon;

  // Close when the user clicks outside or hits Escape.
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div
      ref={containerRef}
      role="group"
      aria-label="Basemap"
      className={cn("flex w-40 flex-col gap-1.5", className)}
    >
      {/* Options stack above the anchor chip when open. */}
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            key="options"
            initial={reduce ? { opacity: 0 } : { opacity: 0, height: 0, y: 8 }}
            animate={reduce ? { opacity: 1 } : { opacity: 1, height: "auto", y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, height: 0, y: 8 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col gap-1.5 overflow-hidden"
            role="radiogroup"
          >
            {OPTIONS.map(({ value: v, label, icon: Icon }) => {
              const selected = value === v;
              return (
                <button
                  key={v}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => {
                    onChange(v);
                    setOpen(false);
                  }}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition-colors",
                    selected
                      ? "border-aqua-500/50 bg-card text-foreground shadow-elev-1"
                      : "border-border bg-card text-muted-foreground shadow-elev-1 hover:text-foreground",
                  )}
                >
                  <Icon
                    className={cn(
                      "size-3.5 shrink-0",
                      selected ? "text-aqua-500" : "text-muted-foreground",
                    )}
                  />
                  <span className="flex-1 text-left">{label}</span>
                  {selected ? <Check className="size-3 text-aqua-500" /> : null}
                </button>
              );
            })}
          </motion.div>
        ) : null}
      </AnimatePresence>

      {/* Anchor chip — stays put while the options expand upward. */}
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={open ? "Hide basemap options" : "Choose basemap"}
        className="inline-flex items-center justify-between gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground shadow-elev-2 transition-colors hover:bg-secondary"
      >
        <span className="inline-flex items-center gap-2">
          <ActiveIcon className="size-4 text-aqua-500" />
          {active.label}
        </span>
        <ChevronUp
          className={cn(
            "size-3 text-muted-foreground transition-transform duration-200",
            // Closed: chevron points UP (signals the menu will expand upward).
            // Open: rotates 180° to point DOWN (signals it will collapse).
            open ? "rotate-180" : "rotate-0",
          )}
          aria-hidden
        />
      </button>
    </div>
  );
}
