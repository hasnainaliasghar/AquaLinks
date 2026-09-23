"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Logo } from "@/components/chrome/logo";
import { ThemeToggle } from "@/components/chrome/theme-toggle";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/methodology", label: "Methodology" },
  { href: "/limitations", label: "Limitations" },
  { href: "/changelog", label: "Changelog" },
  { href: "/about", label: "About" },
];

export function TopNav() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full border-b border-transparent transition-[background,backdrop-filter,border-color] duration-300",
        scrolled && "glass border-border",
      )}
    >
      <div className="container flex h-14 items-center justify-between gap-6">
        <Link href="/" aria-label="AquaLinks home">
          <Logo />
        </Link>
        <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
          {LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "relative rounded-xs px-3 py-1.5 text-sm transition-colors hover:text-foreground",
                  active ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {link.label}
                {active ? (
                  <span className="absolute inset-x-3 -bottom-0.5 h-px bg-foreground" />
                ) : null}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild size="sm" variant="outline" className="hidden sm:inline-flex">
            <Link href="/dashboard">Open app</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/monitor">Start monitoring</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
