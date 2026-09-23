import { FadeIn } from "@/components/motion/fade-in";

const SOURCES = [
  "ESA Copernicus",
  "USGS Landsat",
  "Microsoft Planetary Computer",
  "OpenStreetMap",
  "OpenFreeMap",
  "MapLibre GL",
  "Sentinel-2 L2A",
  "Google AI Studio",
];

export function CitationsMarquee() {
  return (
    <section className="border-y border-border bg-surface-1/50 py-12">
      <div className="container">
        <FadeIn>
          <p className="text-center font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            Built on open data and free infrastructure
          </p>
        </FadeIn>
        <div className="mt-6 overflow-hidden mask-fade-r">
          <div className="flex w-max animate-marquee gap-12 will-change-transform">
            {[...SOURCES, ...SOURCES].map((s, i) => (
              <span
                key={`${s}-${i}`}
                className="whitespace-nowrap font-mono text-xs uppercase tracking-wider text-muted-foreground/80"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
