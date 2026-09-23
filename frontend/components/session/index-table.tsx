"use client";

import { Copy } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TermInfo } from "@/components/ui/term-info";
import { INDEX_GLOSSARY } from "@/components/session/index-grid";
import type { SpectralIndex } from "@/lib/api-types";
import { formatNumber } from "@/lib/format";

export function IndexTable({ indices }: { indices: SpectralIndex[] }) {
  if (indices.length === 0) return null;

  const onCopy = () => {
    const header = ["index", "value", "min", "max", "stddev", "samples", "bands"].join(",");
    const rows = indices.map((i) =>
      [
        i.name,
        i.value.toFixed(4),
        (i.min_value ?? "").toString(),
        (i.max_value ?? "").toString(),
        (i.stddev ?? "").toString(),
        (i.sample_count ?? "").toString(),
        `"${i.bands.join(" ")}"`,
      ].join(","),
    );
    const csv = [header, ...rows].join("\n");
    navigator.clipboard.writeText(csv).then(
      () => toast.success("Index table copied to clipboard as CSV"),
      () => toast.error("Failed to copy to clipboard"),
    );
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle>Index table</CardTitle>
        <Button variant="outline" size="sm" onClick={onCopy}>
          <Copy className="size-3.5" />
          Copy CSV
        </Button>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-2xs uppercase tracking-wider text-muted-foreground">
                <th className="pb-2 pr-3">Index</th>
                <th className="pb-2 pr-3 text-right">Value</th>
                <th className="pb-2 pr-3 text-right">Min</th>
                <th className="pb-2 pr-3 text-right">Max</th>
                <th className="pb-2 pr-3 text-right">σ</th>
                <th className="pb-2 pr-3 text-right">Samples</th>
                <th className="pb-2 pl-3">Bands</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {indices.map((idx) => (
                <tr key={idx.id}>
                  <td className="py-2 pr-3 font-mono text-xs uppercase">
                    <span className="inline-flex items-center gap-1.5">
                      {idx.name}
                      <TermInfo termKey={INDEX_GLOSSARY[idx.name]} />
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-right font-mono">{formatNumber(idx.value)}</td>
                  <td className="py-2 pr-3 text-right font-mono text-muted-foreground">
                    {formatNumber(idx.min_value)}
                  </td>
                  <td className="py-2 pr-3 text-right font-mono text-muted-foreground">
                    {formatNumber(idx.max_value)}
                  </td>
                  <td className="py-2 pr-3 text-right font-mono text-muted-foreground">
                    {formatNumber(idx.stddev)}
                  </td>
                  <td className="py-2 pr-3 text-right font-mono text-muted-foreground">
                    {idx.sample_count ?? "—"}
                  </td>
                  <td className="py-2 pl-3 font-mono text-xs text-muted-foreground">
                    {idx.bands.join(" · ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
