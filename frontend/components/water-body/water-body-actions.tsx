"use client";

import { useRouter } from "next/navigation";
import { Loader2, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDeleteWaterBody, useUpdateWaterBody } from "@/hooks/use-water-bodies";
import type { WaterBody } from "@/lib/api-types";
import { formatLocationLabel, pointToLatLng } from "@/lib/location";

type Props = {
  waterBody: WaterBody;
  align?: "start" | "center" | "end";
  /** Where to send the user after a successful delete. */
  onDeleted?: () => void;
};

export function WaterBodyActions({ waterBody, align = "end", onDeleted }: Props) {
  const [renameOpen, setRenameOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [name, setName] = useState(waterBody.name);
  const centroid = pointToLatLng(waterBody.centroid);
  const locationLabel = formatLocationLabel({
    name: waterBody.name,
    lat: centroid?.lat ?? null,
    lng: centroid?.lng ?? null,
    digits: 3,
  });
  const router = useRouter();
  const updateMutation = useUpdateWaterBody(waterBody.id);
  const deleteMutation = useDeleteWaterBody();

  const submitRename = async () => {
    const trimmed = name.trim();
    if (!trimmed || trimmed === waterBody.name) {
      setRenameOpen(false);
      return;
    }
    try {
      await updateMutation.mutateAsync({ name: trimmed });
      toast.success("Water body renamed");
      setRenameOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not rename");
    }
  };

  const submitDelete = async () => {
    try {
      await deleteMutation.mutateAsync(waterBody.id);
      toast.success(`Deleted “${locationLabel}”`);
      setDeleteOpen(false);
      if (onDeleted) onDeleted();
      else router.push("/water-bodies");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete");
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon-sm" aria-label="Water body actions">
            <MoreHorizontal className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align={align}>
          <DropdownMenuItem
            onSelect={(event) => {
              event.preventDefault();
              setName(waterBody.name);
              setRenameOpen(true);
            }}
          >
            <Pencil className="size-3.5" />
            Rename
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onSelect={(event) => {
              event.preventDefault();
              setDeleteOpen(true);
            }}
          >
            <Trash2 className="size-3.5" />
            Delete…
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename water body</DialogTitle>
            <DialogDescription>
              The new name appears across the dashboard, sessions, and PDF reports.
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void submitRename();
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="wb-rename">Name</Label>
              <Input
                id="wb-rename"
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoFocus
                maxLength={160}
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setRenameOpen(false)}
                disabled={updateMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : null}
                Save
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this water body?</DialogTitle>
            <DialogDescription>
              <strong>“{locationLabel}”</strong> will be removed along with{" "}
              <strong>all of its monitoring sessions and reports</strong>. This can&rsquo;t
              be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void submitDelete()}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Trash2 className="size-3.5" />
              )}
              Delete water body
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
