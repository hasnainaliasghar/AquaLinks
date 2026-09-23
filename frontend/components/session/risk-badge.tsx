"use client";

import { motion, useReducedMotion } from "framer-motion";

import type { RiskLevel } from "@/lib/api-types";
import { cn } from "@/lib/utils";

const COLORS: Record<RiskLevel, string> = {
  low: "var(--risk-low)",
  medium: "var(--risk-medium)",
  high: "var(--risk-high)",
};

export function RiskBadge({
  score,
  level,
  size = 120,
}: {
  score: number;
  level: RiskLevel;
  size?: number;
}) {
  const reduce = useReducedMotion();
  const radius = size / 2 - 8;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(1, score));
  const offset = circumference * (1 - clamped);
  const color = COLORS[level];

  return (
    <div
      role="img"
      aria-label={`Risk level ${level}, score ${(clamped * 100).toFixed(0)} percent`}
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="rotate-[-90deg]">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="var(--border)"
          strokeWidth={6}
          fill="none"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={6}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={circumference}
          initial={reduce ? false : { strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={cn(
            "font-display text-2xl tracking-tight",
            level === "high" && "text-risk-high",
            level === "medium" && "text-risk-medium",
            level === "low" && "text-risk-low",
          )}
        >
          {(clamped * 100).toFixed(0)}
        </span>
        <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
          /100
        </span>
      </div>
    </div>
  );
}
