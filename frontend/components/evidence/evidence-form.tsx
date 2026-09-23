"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Loader2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useSubmitEvidence } from "@/hooks/use-evidence";
import type { Odor, UUID, WaterColor } from "@/lib/api-types";

const SCHEMA = z.object({
  water_color: z.enum([
    "clear",
    "blue",
    "green",
    "brown",
    "yellow",
    "red",
    "black",
    "other",
  ]),
  odor: z.enum([
    "none",
    "earthy",
    "musty",
    "fishy",
    "rotten",
    "chemical",
    "sewage",
    "other",
  ]),
  algae_present: z.boolean(),
  dead_fish_count: z.coerce.number().int().min(0),
  rainfall_mm: z.coerce.number().min(0),
  complaints_count: z.coerce.number().int().min(0),
  notes: z.string().max(2000).optional(),
  reporter_name: z.string().max(120).optional(),
});

type FormValues = z.infer<typeof SCHEMA>;

const COLOR_OPTIONS: WaterColor[] = [
  "clear",
  "blue",
  "green",
  "brown",
  "yellow",
  "red",
  "black",
  "other",
];
const ODOR_OPTIONS: Odor[] = [
  "none",
  "earthy",
  "musty",
  "fishy",
  "rotten",
  "chemical",
  "sewage",
  "other",
];

export function EvidenceForm({
  sessionId,
  onSubmitted,
}: {
  sessionId: UUID;
  onSubmitted?: () => void;
}) {
  const submit = useSubmitEvidence(sessionId);
  const [photo, setPhoto] = useState<File | null>(null);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitSuccessful },
    reset,
  } = useForm<FormValues>({
    resolver: zodResolver(SCHEMA),
    defaultValues: {
      water_color: "clear",
      odor: "none",
      algae_present: false,
      dead_fish_count: 0,
      rainfall_mm: 0,
      complaints_count: 0,
      notes: "",
      reporter_name: "",
    },
  });

  const onLocate = () => {
    if (!("geolocation" in navigator)) {
      toast.error("Geolocation isn’t available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        toast.success("Location captured");
      },
      () => toast.error("Couldn’t read location"),
      { enableHighAccuracy: true, timeout: 8000 },
    );
  };

  const onSubmit = handleSubmit(async (values) => {
    try {
      await submit.mutateAsync({
        payload: {
          ...values,
          latitude: coords?.lat ?? null,
          longitude: coords?.lng ?? null,
        },
        photo,
      });
      toast.success("Evidence submitted — risk is being re-scored");
      reset();
      setPhoto(null);
      onSubmitted?.();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Submission failed";
      toast.error(message);
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Water color" error={errors.water_color?.message}>
          <Select
            value={watch("water_color")}
            onValueChange={(v) => setValue("water_color", v as WaterColor)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Pick a color" />
            </SelectTrigger>
            <SelectContent>
              {COLOR_OPTIONS.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Odor" error={errors.odor?.message}>
          <Select
            value={watch("odor")}
            onValueChange={(v) => setValue("odor", v as Odor)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Pick an odor" />
            </SelectTrigger>
            <SelectContent>
              {ODOR_OPTIONS.map((o) => (
                <SelectItem key={o} value={o}>
                  {o}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      </div>

      <Field label="Algae visible">
        <div className="flex items-center gap-3">
          <Switch
            checked={watch("algae_present")}
            onCheckedChange={(v) => setValue("algae_present", v)}
            aria-label="Algae present"
          />
          <span className="text-sm text-muted-foreground">
            {watch("algae_present") ? "Yes" : "No"}
          </span>
        </div>
      </Field>

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Dead fish count" error={errors.dead_fish_count?.message}>
          <Input type="number" min={0} {...register("dead_fish_count")} />
        </Field>
        <Field label="Rainfall (mm, last 24h)" error={errors.rainfall_mm?.message}>
          <Input type="number" min={0} step="0.1" {...register("rainfall_mm")} />
        </Field>
        <Field label="Public complaints" error={errors.complaints_count?.message}>
          <Input type="number" min={0} {...register("complaints_count")} />
        </Field>
      </div>

      <Field label="Notes" error={errors.notes?.message}>
        <Textarea
          rows={4}
          placeholder="Anything else the field team needs to remember…"
          {...register("notes")}
        />
      </Field>

      <Field label="Reporter (optional)" error={errors.reporter_name?.message}>
        <Input placeholder="Your name" {...register("reporter_name")} />
      </Field>

      <Field label="Photo (optional)">
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          className="block w-full text-sm text-muted-foreground file:mr-3 file:rounded-xs file:border-0 file:bg-secondary file:px-3 file:py-2 file:text-xs file:font-medium file:uppercase file:tracking-wider hover:file:bg-subtle"
          onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
        />
        {photo ? (
          <p className="mt-2 font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            {photo.name} · {(photo.size / 1024).toFixed(0)} kB
          </p>
        ) : null}
      </Field>

      <Field label="Coordinates (optional)">
        <div className="flex items-center gap-3">
          <Button type="button" size="sm" variant="outline" onClick={onLocate}>
            Use device GPS
          </Button>
          {coords ? (
            <span className="font-mono text-xs text-muted-foreground">
              {coords.lat.toFixed(5)}, {coords.lng.toFixed(5)}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">No coordinates attached</span>
          )}
        </div>
      </Field>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={submit.isPending}>
          {submit.isPending ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
          {submit.isPending ? "Submitting…" : "Submit evidence"}
        </Button>
        {isSubmitSuccessful ? (
          <span className="font-mono text-2xs uppercase tracking-wider text-risk-low-fg dark:text-risk-low">
            Recorded
          </span>
        ) : null}
      </div>
    </form>
  );
}

function Field({
  label,
  children,
  error,
}: {
  label: string;
  children: React.ReactNode;
  error?: string;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
      {error ? <p className="text-2xs text-risk-high">{error}</p> : null}
    </div>
  );
}
