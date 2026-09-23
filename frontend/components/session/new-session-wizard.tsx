"use client";

import { ArrowLeft, ArrowRight, ArrowUpRight, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Logo } from "@/components/chrome/logo";
import { MapSearch, type MapSearchPick } from "@/components/map/map-search";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { useCreateSession } from "@/hooks/use-sessions";
import type { GeoJSONPolygon } from "@/lib/api-types";
import { parseCoords } from "@/lib/geocode";
import { polygonAreaKm2, polygonCentroid } from "@/lib/geo";
import { formatArea } from "@/lib/format";
import { formatLocationLabel } from "@/lib/location";
import { formatLatLng } from "@/lib/point";
import { cn } from "@/lib/utils";

type Step = 1 | 2 | 3;

const STEPS: Record<Step, { label: string; hint: string }> = {
  1: { label: "Area", hint: "Draw or paste an AOI" },
  2: { label: "Window", hint: "Pick a date range" },
  3: { label: "Review", hint: "Confirm and launch" },
};

const today = () => new Date().toISOString().slice(0, 10);
const daysAgo = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
};

export function NewSessionWizard({
  polygon,
  suggestedName,
  onSearchPick,
}: {
  polygon: GeoJSONPolygon | null;
  /**
   * Name suggested by an upstream picker (e.g. the map search). Wins over
   * the centroid-derived default but never overrides something the user
   * has typed.
   */
  suggestedName?: string | null;
  /** Forwarded to the embedded search bar so picking a result drops the pin. */
  onSearchPick?: (pick: MapSearchPick) => void;
}) {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [name, setName] = useState("");
  const [nameEdited, setNameEdited] = useState(false);
  const [coordsInput, setCoordsInput] = useState("");
  const [startDate, setStartDate] = useState(daysAgo(30));
  const [endDate, setEndDate] = useState(today());
  const [cloud, setCloud] = useState(30);
  const createSession = useCreateSession();

  // Mirror the polygon centroid into the coordinate field (unless the
  // user has typed something we haven't applied yet).
  useEffect(() => {
    if (!polygon) return;
    const [lng, lat] = polygonCentroid(polygon);
    setCoordsInput(`${lat.toFixed(4)}, ${lng.toFixed(4)}`);
  }, [polygon]);

  const applyCoords = () => {
    const parsed = parseCoords(coordsInput);
    if (!parsed) {
      toast.error("Enter coordinates as `lat, lng` in decimal degrees (e.g. 45.987, 9.252).");
      return;
    }
    onSearchPick?.({
      name: formatLatLng(parsed.lng, parsed.lat, 4),
      lng: parsed.lng,
      lat: parsed.lat,
      source: "coords",
    });
    toast.success("Pin moved to those coordinates.");
  };

  const area = useMemo(() => (polygon ? polygonAreaKm2(polygon) : 0), [polygon]);

  // Pre-fill the AOI name with a stable location label:
  // `Place name (lat · lng)` or `lat · lng` when no name is available.
  // Stop auto-filling once the user edits manually.
  useEffect(() => {
    if (nameEdited) return;
    if (!polygon) return;
    const [lng, lat] = polygonCentroid(polygon);
    setName(formatLocationLabel({ name: suggestedName, lng, lat, digits: 3 }));
  }, [polygon, suggestedName, nameEdited]);

  const canAdvance =
    step === 1 ? Boolean(polygon) && name.trim().length > 0 : step === 2 ? startDate <= endDate : true;

  const submit = async () => {
    if (!polygon) return;
    try {
      const session = await createSession.mutateAsync({
        new_water_body: {
          name: name.trim(),
          geometry: polygon,
          source: "user_drawn",
        },
        start_date: startDate,
        end_date: endDate,
        max_cloud_cover: cloud,
      });
      toast.success("Session queued — fetching imagery now");
      router.push(`/sessions/${session.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not create session");
    }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-border px-5 py-4">
        <div className="flex items-center justify-between">
          <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            New session
          </p>
          <Badge variant="muted">{STEPS[step].label}</Badge>
        </div>
        <ol className="mt-3 flex items-center gap-2">
          {([1, 2, 3] as Step[]).map((s) => (
            <li key={s} className="flex flex-1 items-center gap-2">
              <span
                className={cn(
                  "size-2 rounded-full transition-colors",
                  step >= s ? "bg-aqua-500" : "bg-border",
                )}
              />
              <span
                className={cn(
                  "text-xs",
                  step === s ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {STEPS[s].label}
              </span>
            </li>
          ))}
        </ol>
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        {step === 1 ? (
          <div className="space-y-5">
            <div className="space-y-2">
              <Label>Find a water body</Label>
              <MapSearch onPick={(pick) => onSearchPick?.(pick)} />
              <p className="text-2xs text-muted-foreground">
                Search by name, paste decimal coordinates, or click anywhere on the
                map to drop a pin.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Water body name</Label>
              <Input
                id="name"
                placeholder="Lake Como"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setNameEdited(true);
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="coords">Coordinates</Label>
              <div className="flex gap-2">
                <Input
                  id="coords"
                  placeholder="45.987, 9.252"
                  inputMode="decimal"
                  spellCheck={false}
                  autoComplete="off"
                  value={coordsInput}
                  onChange={(e) => setCoordsInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      applyCoords();
                    }
                  }}
                  className="flex-1 font-mono"
                />
                <Button type="button" size="sm" variant="outline" onClick={applyCoords}>
                  Set pin
                </Button>
              </div>
              <p className="text-2xs text-muted-foreground">
                Decimal degrees, latitude first. Press Enter or hit
                <span className="mx-1 font-medium">Set pin</span> to move the AOI.
              </p>
            </div>
            <div className="space-y-2">
              <Label>Area of interest</Label>
              {polygon ? (
                <div className="rounded-md border border-border bg-surface-1 p-3 text-sm">
                  <p className="font-medium">Captured from the map</p>
                  <p className="text-muted-foreground">
                    Estimated area · {formatArea(area)}
                  </p>
                </div>
              ) : (
                <p className="rounded-md border border-dashed border-border bg-surface-1 p-3 text-sm text-muted-foreground">
                  Pick a target above and a 1 km buffer around the pin becomes the AOI.
                </p>
              )}
            </div>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="start">Start</Label>
                <Input
                  id="start"
                  type="date"
                  value={startDate}
                  max={endDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end">End</Label>
                <Input
                  id="end"
                  type="date"
                  value={endDate}
                  min={startDate}
                  max={today()}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Maximum cloud cover</Label>
                <span className="font-mono text-xs text-muted-foreground">
                  &lt; {cloud}%
                </span>
              </div>
              <Slider
                min={0}
                max={80}
                step={1}
                value={[cloud]}
                onValueChange={(v) => setCloud(v[0] ?? 30)}
                aria-label="Maximum cloud cover"
              />
              <p className="text-xs text-muted-foreground">
                The latest scene matching this threshold is chosen. Lower is stricter.
              </p>
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <dl className="space-y-3 text-sm">
            <Row label="AOI name">{name || "—"}</Row>
            <Row label="Approx area">{formatArea(area)}</Row>
            <Row label="Window">
              {startDate} → {endDate}
            </Row>
            <Row label="Max cloud cover">&lt; {cloud}%</Row>
            <Row label="Provider">Microsoft Planetary Computer · Sentinel-2 L2A</Row>
          </dl>
        ) : null}
      </div>

      <footer className="space-y-3 border-t border-border px-5 py-4">
        {step < 3 ? (
          <div className="flex items-center justify-between gap-3">
            <Button
              variant="outline"
              size="sm"
              disabled={step === 1}
              onClick={() => setStep((s) => (s > 1 ? ((s - 1) as Step) : s))}
            >
              <ArrowLeft className="size-3.5" />
              Back
            </Button>
            <Button
              size="sm"
              disabled={!canAdvance}
              onClick={() => setStep((s) => (s < 3 ? ((s + 1) as Step) : s))}
            >
              Continue
              <ArrowRight className="size-3.5" />
            </Button>
          </div>
        ) : (
          <>
            <button
              type="button"
              disabled={createSession.isPending || !polygon}
              onClick={submit}
              className="group relative flex w-full items-center gap-3 overflow-hidden rounded-full border border-aqua-500/40 bg-gradient-to-r from-aqua-500/15 via-aqua-500/8 to-transparent px-3 py-2.5 text-left text-sm font-medium shadow-elev-2 transition-[transform,box-shadow,border-color] duration-200 ease-brand hover:-translate-y-0.5 hover:border-aqua-500/60 hover:shadow-elev-3 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-elev-2"
            >
              <span className="flex size-9 shrink-0 items-center justify-center">
                {createSession.isPending ? (
                  <Loader2 className="size-5 animate-spin text-aqua-500" />
                ) : (
                  <Logo showText={false} size="sm" />
                )}
              </span>
              <span className="flex flex-1 flex-col leading-tight">
                <span>{createSession.isPending ? "Launching session…" : "Launch session"}</span>
                <span className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
                  Sentinel-2 → indices → risk
                </span>
              </span>
              <ArrowUpRight className="size-4 shrink-0 text-aqua-500 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </button>
            <Button
              variant="outline"
              size="sm"
              disabled={createSession.isPending}
              onClick={() => setStep(2)}
              className="w-full"
            >
              <ArrowLeft className="size-3.5" />
              Back to window
            </Button>
          </>
        )}
      </footer>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border/60 pb-2 last:border-b-0">
      <dt className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="text-right">{children}</dd>
    </div>
  );
}
