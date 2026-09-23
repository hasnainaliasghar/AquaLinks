"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { FadeIn } from "@/components/motion/fade-in";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STORAGE_KEY = "aqualens.prefs";

type Preferences = {
  defaultLookbackDays: number;
  defaultCloud: number;
};

const DEFAULTS: Preferences = { defaultLookbackDays: 30, defaultCloud: 30 };

function loadPrefs(): Preferences {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    return { ...DEFAULTS, ...(JSON.parse(raw) as Partial<Preferences>) };
  } catch {
    return DEFAULTS;
  }
}

function savePrefs(prefs: Preferences) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export default function SettingsPage() {
  const { theme, setTheme, themes } = useTheme();
  const [prefs, setPrefs] = useState<Preferences>(DEFAULTS);

  useEffect(() => {
    setPrefs(loadPrefs());
  }, []);

  useEffect(() => {
    savePrefs(prefs);
  }, [prefs]);

  return (
    <div className="container max-w-3xl py-10">
      <FadeIn>
        <header>
          <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            Preferences
          </p>
          <h1 className="mt-1 font-display text-3xl tracking-tight sm:text-4xl">
            Settings
          </h1>
          <p className="mt-2 text-muted-foreground">
            These choices are saved locally to this browser. They don’t change the
            backend defaults, just the values the monitor wizard pre-fills.
          </p>
        </header>
      </FadeIn>

      <div className="mt-8 space-y-4">
        <FadeIn>
          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Label>Theme</Label>
              <Select value={theme} onValueChange={(v) => setTheme(v)}>
                <SelectTrigger className="max-w-xs">
                  <SelectValue placeholder="Theme" />
                </SelectTrigger>
                <SelectContent>
                  {themes.map((t) => (
                    <SelectItem key={t} value={t} className="capitalize">
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>
        </FadeIn>

        <FadeIn>
          <Card>
            <CardHeader>
              <CardTitle>Monitor defaults</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Default look-back window</Label>
                  <span className="font-mono text-xs text-muted-foreground">
                    {prefs.defaultLookbackDays} days
                  </span>
                </div>
                <Slider
                  min={1}
                  max={120}
                  value={[prefs.defaultLookbackDays]}
                  onValueChange={(v) =>
                    setPrefs((p) => ({ ...p, defaultLookbackDays: v[0] ?? p.defaultLookbackDays }))
                  }
                  aria-label="Default look-back days"
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Maximum cloud cover</Label>
                  <span className="font-mono text-xs text-muted-foreground">
                    &lt; {prefs.defaultCloud}%
                  </span>
                </div>
                <Slider
                  min={0}
                  max={80}
                  value={[prefs.defaultCloud]}
                  onValueChange={(v) =>
                    setPrefs((p) => ({ ...p, defaultCloud: v[0] ?? p.defaultCloud }))
                  }
                  aria-label="Default max cloud cover"
                />
              </div>
            </CardContent>
          </Card>
        </FadeIn>
      </div>
    </div>
  );
}
