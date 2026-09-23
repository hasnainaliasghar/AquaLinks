import { cn } from "@/lib/utils";

type Size = "sm" | "md" | "lg" | "xl";

const SIZES: Record<Size, { container: string; text: string; subtext: string }> = {
  sm: { container: "w-8 h-8", text: "text-base", subtext: "hidden" },
  md: { container: "w-10 h-10", text: "text-lg", subtext: "text-[10px]" },
  lg: { container: "w-[3.25rem] h-[3.25rem]", text: "text-2xl", subtext: "text-xs" },
  xl: { container: "w-[4.5rem] h-[4.5rem]", text: "text-3xl", subtext: "text-sm" },
};

// Orbit ring spins noticeably faster than the satellite — both have been
// sped up from their previous slow pace.
const ORBIT_SPIN_CLASS = "animate-[spin_6s_linear_infinite]";
const SATELLITE_SPIN_CLASS = "animate-[spin_12s_linear_infinite]";

export function Logo({
  className,
  showText = true,
  showSubtext = false,
  size = "md",
  muted = false,
  glow = true,
}: {
  className?: string;
  showText?: boolean;
  showSubtext?: boolean;
  size?: Size;
  muted?: boolean;
  glow?: boolean;
}) {
  const sizing = SIZES[size];

  return (
    <div className={cn("group flex select-none items-center gap-2.5", className)}>
      <div
        className={cn("relative", sizing.container, muted && "saturate-[0.42] brightness-[1.24]")}
        style={glow ? { filter: "drop-shadow(var(--logo-glow))" } : undefined}
      >
        <svg
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={cn("h-full w-full overflow-visible", muted && "opacity-60")}
          aria-hidden
        >
          <defs>
            <linearGradient
              id="aqua-logo-gradient"
              x1="50"
              y1="0"
              x2="50"
              y2="100"
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0%" stopColor="var(--logo-from)" />
              <stop offset="50%" stopColor="var(--logo-mid)" />
              <stop offset="100%" stopColor="var(--logo-to)" />
            </linearGradient>
            <linearGradient
              id="aqua-sat-panel-gradient"
              x1="-7.4"
              y1="0"
              x2="7.4"
              y2="0"
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0%" stopColor="var(--logo-from)" />
              <stop offset="45%" stopColor="var(--logo-mid)" />
              <stop offset="100%" stopColor="var(--logo-to)" />
            </linearGradient>
            <linearGradient
              id="aqua-sat-body-gradient"
              x1="-2.1"
              y1="-1.6"
              x2="2.1"
              y2="1.6"
              gradientUnits="userSpaceOnUse"
            >
              <stop offset="0%" stopColor="#f8fdff" stopOpacity="0.96" />
              <stop offset="100%" stopColor="var(--logo-mid)" stopOpacity="0.9" />
            </linearGradient>
            <radialGradient id="aqua-sat-glow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="var(--logo-mid)" stopOpacity="0.45" />
              <stop offset="100%" stopColor="var(--logo-mid)" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Outer orbit ring */}
          <g className={cn("origin-center", ORBIT_SPIN_CLASS)}>
            <g className="opacity-50 transition-opacity duration-500 group-hover:opacity-80">
              <circle
                cx="50"
                cy="50"
                r="43"
                stroke="url(#aqua-logo-gradient)"
                strokeWidth="1.7"
                strokeDasharray="56 38 56 38 56 26"
                strokeLinecap="round"
              />
            </g>
          </g>

          {/* Satellite */}
          <g className={cn("origin-center", SATELLITE_SPIN_CLASS)}>
            <g transform="translate(50 6) rotate(14) scale(2.05)">
              <ellipse cx="0" cy="0" rx="8.2" ry="3.9" fill="url(#aqua-sat-glow)" opacity="0.26" />

              {/* Solar arrays */}
              <rect
                x="-7.4"
                y="-1.45"
                width="4.2"
                height="2.9"
                rx="0.65"
                fill="url(#aqua-sat-panel-gradient)"
                opacity="0.94"
              />
              <rect
                x="3.2"
                y="-1.45"
                width="4.2"
                height="2.9"
                rx="0.65"
                fill="url(#aqua-sat-panel-gradient)"
                opacity="0.94"
              />
              <path
                d="M-5.9 -1.1 V1.1 M-4.6 -1.1 V1.1 M4.6 -1.1 V1.1 M5.9 -1.1 V1.1"
                stroke="white"
                strokeOpacity="0.36"
                strokeWidth="0.26"
                strokeLinecap="round"
              />

              {/* Struts */}
              <path
                d="M-3.2 0 H-2.1 M2.1 0 H3.2"
                stroke="var(--logo-mid)"
                strokeWidth="0.55"
                strokeLinecap="round"
                opacity="0.9"
              />

              {/* Main bus */}
              <rect
                x="-2.1"
                y="-1.6"
                width="4.2"
                height="3.2"
                rx="0.95"
                fill="url(#aqua-sat-body-gradient)"
                stroke="white"
                strokeOpacity="0.45"
                strokeWidth="0.32"
              />
              <rect
                x="-1.1"
                y="-0.72"
                width="2.2"
                height="1.44"
                rx="0.38"
                fill="var(--logo-dot)"
                opacity="0.9"
              />
              <circle cx="-0.32" cy="0" r="0.26" fill="white" opacity="0.82" />

              {/* Dish and antenna */}
              <path d="M1.45 -0.95 L2.7 -2.05" stroke="var(--logo-mid)" strokeWidth="0.35" />
              <path
                d="M2.95 -2.25 A1.35 1.1 0 0 1 4.05 -1.15"
                stroke="white"
                strokeOpacity="0.78"
                strokeWidth="0.34"
                fill="none"
              />
              <circle cx="4.18" cy="-1.05" r="0.22" fill="white" opacity="0.9" />
            </g>
          </g>

          {/* Inner focus ring — static, light wash */}
          <circle
            cx="50"
            cy="50"
            r="38"
            stroke="url(#aqua-logo-gradient)"
            strokeWidth="0.5"
            className="opacity-25"
          />

          {/* Central water drop — gentle pulse, scales on hover */}
          <g className="origin-center transition-transform duration-500 ease-out group-hover:scale-110">
            <g className="origin-center scale-75">
              <path
                d="M50 18 C50 18 28 48 28 64 C28 76.15 37.85 86 50 86 C62.15 86 72 76.15 72 64 C72 48 50 18 50 18 Z"
                fill="url(#aqua-logo-gradient)"
                className="animate-pulse"
                style={{ animationDuration: "4s" }}
              />
              <path
                d="M40 53 Q 35 63 42 73"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                className="opacity-40"
              />
            </g>
          </g>

        </svg>
      </div>

      {showText && (
        <div className="flex flex-col justify-center leading-none">
          <span
            className={cn(
              "bg-clip-text font-display font-medium tracking-tight text-transparent",
              sizing.text,
            )}
            style={{
              backgroundImage:
                "linear-gradient(to right, var(--logo-from), var(--logo-mid), var(--logo-to))",
            }}
          >
            AquaLinks
          </span>
          {showSubtext && size !== "sm" && (
            <span
              className={cn(
                "mt-1 font-mono uppercase tracking-[0.2em] text-muted-foreground",
                sizing.subtext,
              )}
            >
              Sentinel-2
            </span>
          )}
        </div>
      )}
    </div>
  );
}
