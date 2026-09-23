"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";
import { CheckSquare2, Droplet, Loader2, Square, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { FadeIn } from "@/components/motion/fade-in";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { WaterBodyActions } from "@/components/water-body/water-body-actions";
import { useBulkDeleteWaterBodies, useWaterBodies } from "@/hooks/use-water-bodies";
import { formatArea, formatDateTime } from "@/lib/format";
import { formatLocationLabel, pointToLatLng } from "@/lib/location";

const MiniMap = dynamic(() => import("@/components/map/mini-map").then((m) => m.MiniMap), {
  ssr: false,
});

export default function WaterBodiesPage() {
  const { data, isLoading } = useWaterBodies();
  const bulkDelete = useBulkDeleteWaterBodies();
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const ids = useMemo(() => data?.map((wb) => wb.id) ?? [], [data]);
  const selectedCount = selectedIds.size;
  const allVisibleSelected = ids.length > 0 && ids.every((id) => selectedIds.has(id));

  const toggleSelected = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllVisible = () => {
    setSelectedIds(new Set(ids));
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
  };

  const openSelectionMode = () => {
    setSelectionMode(true);
    clearSelection();
  };

  const closeSelectionMode = () => {
    setSelectionMode(false);
    clearSelection();
  };

  const submitBulkDelete = async () => {
    if (selectedCount === 0) return;
    try {
      const result = await bulkDelete.mutateAsync({ ids: Array.from(selectedIds) });
      const noun = result.deleted_count === 1 ? "water body" : "water bodies";
      toast.success(`Deleted ${result.deleted_count} ${noun}.`);
      setConfirmDeleteOpen(false);
      closeSelectionMode();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete selected water bodies.");
    }
  };

  return (
    <div className="container max-w-7xl py-10">
      <FadeIn>
        <header className="flex items-end justify-between gap-3">
          <div>
            <p className="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
              Library
            </p>
            <h1 className="mt-1 font-display text-3xl tracking-tight sm:text-4xl">
              Water bodies
            </h1>
            <p className="mt-2 max-w-xl text-muted-foreground">
              Every AOI you’ve saved. Open one to see its full session history and
              compare indices over time.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {selectionMode ? (
              <>
                <Button
                  type="button"
                  variant="outline"
                  onClick={allVisibleSelected ? clearSelection : selectAllVisible}
                  disabled={ids.length === 0}
                >
                  {allVisibleSelected ? (
                    <>
                      <CheckSquare2 className="size-4" />
                      All selected
                    </>
                  ) : (
                    <>
                      <Square className="size-4" />
                      Select all
                    </>
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={clearSelection}
                  disabled={selectedCount === 0}
                >
                  Clear
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => setConfirmDeleteOpen(true)}
                  disabled={selectedCount === 0 || bulkDelete.isPending}
                >
                  {bulkDelete.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Trash2 className="size-4" />
                  )}
                  Delete selected ({selectedCount})
                </Button>
                <Button type="button" variant="ghost" onClick={closeSelectionMode}>
                  <X className="size-4" />
                  Done
                </Button>
              </>
            ) : (
              <>
                <Button asChild>
                  <Link href="/monitor">Add via map</Link>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={openSelectionMode}
                  disabled={!data || data.length === 0}
                >
                  Edit list
                </Button>
              </>
            )}
          </div>
        </header>
      </FadeIn>

      <section className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-72 w-full rounded-xl" />
          ))
        ) : data && data.length > 0 ? (
          data.map((wb) => {
            const centroid = pointToLatLng(wb.centroid);
            const locationLabel = formatLocationLabel({
              name: wb.name,
              lat: centroid?.lat ?? null,
              lng: centroid?.lng ?? null,
              digits: 3,
            });
            return (
              <FadeIn key={wb.id}>
                <Card className="group relative overflow-hidden transition-shadow hover:shadow-elev-2">
                  {selectionMode ? (
                    <>
                      <button
                        type="button"
                        onClick={() => toggleSelected(wb.id)}
                        className="absolute top-3 right-3 z-20 rounded-sm bg-background/80 p-1 text-foreground shadow-sm ring-1 ring-border"
                        aria-label={
                          selectedIds.has(wb.id)
                            ? `Unselect ${locationLabel}`
                            : `Select ${locationLabel}`
                        }
                      >
                        {selectedIds.has(wb.id) ? (
                          <CheckSquare2 className="size-4 text-aqua-500" />
                        ) : (
                          <Square className="size-4 text-muted-foreground" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleSelected(wb.id)}
                        className="block w-full text-left focus-visible:outline-none"
                      >
                        <MiniMap polygon={wb.geometry} />
                        <CardContent className="space-y-2 p-5 pr-12">
                          <p className="inline-flex items-center gap-2 font-display text-lg tracking-tight">
                            <Droplet className="size-4 text-aqua-500" />
                            {locationLabel}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatArea(wb.area_km2)} · added {formatDateTime(wb.created_at)}
                          </p>
                        </CardContent>
                      </button>
                    </>
                  ) : (
                    <>
                      <Link
                        href={`/water-bodies/${wb.id}`}
                        className="block focus-visible:outline-none"
                      >
                        <MiniMap polygon={wb.geometry} />
                        <CardContent className="space-y-2 p-5 pr-12">
                          <p className="inline-flex items-center gap-2 font-display text-lg tracking-tight">
                            <Droplet className="size-4 text-aqua-500" />
                            {locationLabel}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatArea(wb.area_km2)} · added {formatDateTime(wb.created_at)}
                          </p>
                        </CardContent>
                      </Link>
                      <div className="absolute right-3 bottom-3 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                        <WaterBodyActions waterBody={wb} />
                      </div>
                    </>
                  )}
                </Card>
              </FadeIn>
            );
          })
        ) : (
          <Card className="col-span-full border-dashed">
            <CardContent className="py-10 text-center">
              <p className="font-display text-lg tracking-tight">No water bodies yet.</p>
              <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
                Pick an area on the monitor page — search a place, paste coordinates,
                or tap the map. AquaLinks saves the AOI automatically so you can re-run
                sessions later.
              </p>
              <Button asChild className="mt-4">
                <Link href="/monitor">Open monitor</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </section>

      <Dialog open={confirmDeleteOpen} onOpenChange={setConfirmDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete selected water bodies?</DialogTitle>
            <DialogDescription>
              You selected <strong>{selectedCount}</strong>{" "}
              {selectedCount === 1 ? "water body" : "water bodies"}. This permanently removes
              each selection and all related sessions, reports, indices, and evidence.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmDeleteOpen(false)}
              disabled={bulkDelete.isPending}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void submitBulkDelete()}
              disabled={selectedCount === 0 || bulkDelete.isPending}
            >
              {bulkDelete.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Trash2 className="size-4" />
              )}
              Delete selected
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
