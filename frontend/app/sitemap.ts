import type { MetadataRoute } from "next";

import { env } from "@/lib/env";

const ROUTES = [
  "",
  "/methodology",
  "/limitations",
  "/about",
  "/changelog",
  "/dashboard",
  "/monitor",
  "/sessions",
  "/water-bodies",
  "/settings",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return ROUTES.map((route) => ({
    url: `${env.NEXT_PUBLIC_SITE_URL}${route}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: route === "" ? 1.0 : 0.6,
  }));
}
