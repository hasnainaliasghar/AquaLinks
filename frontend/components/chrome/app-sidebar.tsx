"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Compass, Droplet, LayoutDashboard, Map, Settings } from "lucide-react";

import { Logo } from "@/components/chrome/logo";
import { ThemeToggle } from "@/components/chrome/theme-toggle";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/monitor", label: "Monitor", icon: Compass },
  { href: "/sessions", label: "Sessions", icon: Activity },
  { href: "/water-bodies", label: "Water bodies", icon: Droplet },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <aside
      aria-label="Primary navigation"
      className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border bg-surface-1/60 backdrop-blur lg:flex"
    >
      <div className="flex h-14 items-center justify-between border-b border-border px-4">
        <Link href="/" aria-label="AquaLinks home">
          <Logo />
        </Link>
        <ThemeToggle />
      </div>
      <nav className="flex-1 space-y-0.5 p-3">
        {ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
              )}
            >
              <Icon className="size-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-3 text-2xs uppercase tracking-wider text-muted-foreground">
        <p>
          Press <kbd className="rounded border border-border px-1 py-0.5 font-mono">Ctrl K</kbd> to search
        </p>
      </div>
    </aside>
  );
}

export function MobileTabBar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary navigation"
      className="fixed inset-x-0 bottom-0 z-30 flex h-16 items-center justify-around border-t border-border bg-surface-1/95 backdrop-blur lg:hidden"
    >
      {ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-col items-center justify-center gap-0.5 px-3 py-2 text-2xs",
              active ? "text-foreground" : "text-muted-foreground",
            )}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export { Map as MapIcon };
