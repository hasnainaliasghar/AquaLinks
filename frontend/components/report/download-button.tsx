"use client";

import { Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import type { UUID } from "@/lib/api-types";

export function DownloadReportButton({
  sessionId,
  className,
}: {
  sessionId: UUID;
  className?: string;
}) {
  const dateTag = new Date().toISOString().slice(0, 10).replaceAll("-", "");
  return (
    <Button asChild className={className}>
      <a
        href={api.reportUrl(sessionId)}
        download={`aqualinks-analysis-${dateTag}.pdf`}
        rel="noreferrer"
      >
        <Download className="size-4" />
        Download PDF
      </a>
    </Button>
  );
}
