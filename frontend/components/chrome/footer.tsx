import Link from "next/link";

import { Logo } from "@/components/chrome/logo";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "/monitor", label: "Start a session" },
      { href: "/dashboard", label: "Open the app" },
      { href: "/methodology", label: "Methodology" },
      { href: "/changelog", label: "Changelog" },
    ],
  },
  {
    title: "Project",
    links: [
      { href: "/about", label: "About" },
      { href: "/limitations", label: "Limitations" },
      { href: "https://github.com/talhaabidj1/aqualens", label: "GitHub" },
    ],
  },
  {
    title: "Data",
    links: [
      { href: "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a", label: "Sentinel-2 L2A" },
      { href: "https://openfreemap.org", label: "OpenFreeMap" },
      { href: "https://maplibre.org", label: "MapLibre" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-border bg-surface-1">
      <div className="container py-12">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_3fr]">
          <div className="space-y-3">
            <Logo />
            <p className="max-w-sm text-sm text-muted-foreground">
              AquaLinks is an autonomous freshwater monitoring agent. It produces advisory
              risk indicators, not certified water-safety results.
            </p>
            <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
              © {new Date().getFullYear()} Talha Abid · MIT License
            </p>
          </div>
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
            {COLUMNS.map((col) => (
              <div key={col.title} className="space-y-3">
                <h4 className="text-2xs font-medium uppercase tracking-wider text-muted-foreground">
                  {col.title}
                </h4>
                <ul className="space-y-2 text-sm">
                  {col.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="text-foreground/85 transition-colors hover:text-foreground"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-10 border-t border-border pt-6 text-xs text-muted-foreground">
          Sentinel-2 imagery © European Union, contains modified Copernicus Sentinel data
          accessed via the Microsoft Planetary Computer. Base map © OpenStreetMap
          contributors, ODbL 1.0.
        </div>
      </div>
    </footer>
  );
}
