import type { Metadata } from "next";
import { env } from "@/lib/env";

const SITE_NAME = "AquaLinks";
const DEFAULT_DESCRIPTION =
  "Autonomous freshwater monitoring agent. Retrieve Sentinel-2 imagery, compute spectral indices, fuse field evidence, and export advisory risk reports.";

export function buildMetadata(args: {
  title?: string;
  description?: string;
  path?: string;
  ogImage?: string;
}): Metadata {
  const title = args.title ? `${args.title} · ${SITE_NAME}` : `${SITE_NAME} — water you can monitor`;
  const description = args.description ?? DEFAULT_DESCRIPTION;
  const url = `${env.NEXT_PUBLIC_SITE_URL}${args.path ?? "/"}`;
  return {
    metadataBase: new URL(env.NEXT_PUBLIC_SITE_URL),
    title,
    description,
    applicationName: SITE_NAME,
    authors: [{ name: "Talha Abid" }],
    creator: "Talha Abid",
    keywords: [
      "water quality",
      "remote sensing",
      "Sentinel-2",
      "spectral indices",
      "freshwater monitoring",
      "agentic AI",
      "environmental monitoring",
    ],
    openGraph: {
      type: "website",
      url,
      siteName: SITE_NAME,
      title,
      description,
      images: args.ogImage ? [{ url: args.ogImage, width: 1200, height: 630 }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: args.ogImage ? [args.ogImage] : undefined,
    },
    alternates: { canonical: url },
    robots: { index: true, follow: true },
  };
}
