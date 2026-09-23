"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, Compass, Droplet, LayoutDashboard, Settings, Sparkles } from "lucide-react";

import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";

export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const go = (path: string) => {
    setOpen(false);
    router.push(path);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-xl gap-0 overflow-hidden p-0">
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <DialogDescription className="sr-only">
          Search for sessions, water bodies, or pages, or trigger an action.
        </DialogDescription>
        <Command shouldFilter>
          <CommandInput placeholder="Search AquaLinks — sessions, water bodies, pages…" />
          <CommandList>
            <CommandEmpty>No results.</CommandEmpty>
            <CommandGroup heading="Actions">
              <CommandItem onSelect={() => go("/monitor")}>
                <Sparkles className="size-4" />
                Start a new monitoring session
                <CommandShortcut>N</CommandShortcut>
              </CommandItem>
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Navigate">
              <CommandItem onSelect={() => go("/dashboard")}>
                <LayoutDashboard className="size-4" />
                Dashboard
              </CommandItem>
              <CommandItem onSelect={() => go("/monitor")}>
                <Compass className="size-4" />
                Monitor
              </CommandItem>
              <CommandItem onSelect={() => go("/sessions")}>
                <Activity className="size-4" />
                Sessions
              </CommandItem>
              <CommandItem onSelect={() => go("/water-bodies")}>
                <Droplet className="size-4" />
                Water bodies
              </CommandItem>
              <CommandItem onSelect={() => go("/settings")}>
                <Settings className="size-4" />
                Settings
              </CommandItem>
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Learn">
              <CommandItem onSelect={() => go("/methodology")}>Methodology</CommandItem>
              <CommandItem onSelect={() => go("/limitations")}>Limitations</CommandItem>
              <CommandItem onSelect={() => go("/about")}>About</CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
