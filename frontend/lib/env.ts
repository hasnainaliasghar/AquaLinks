import { z } from "zod";

function normalizeUrl(val: string | undefined, defaultUrl: string): string {
  if (!val || typeof val !== "string") return defaultUrl;
  let trimmed = val.trim();
  if (!trimmed) return defaultUrl;
  if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
    trimmed = `https://${trimmed}`;
  }
  return trimmed.replace(/\/+$/, "");
}

const rawApiUrl = normalizeUrl(process.env.NEXT_PUBLIC_API_URL, "http://localhost:8000");
const rawSiteUrl = normalizeUrl(process.env.NEXT_PUBLIC_SITE_URL, "http://localhost:3000");

const ClientEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().default("http://localhost:8000"),
  NEXT_PUBLIC_SITE_URL: z.string().url().default("http://localhost:3000"),
});

export type ClientEnv = z.infer<typeof ClientEnvSchema>;

function getEnv(): ClientEnv {
  const result = ClientEnvSchema.safeParse({
    NEXT_PUBLIC_API_URL: rawApiUrl,
    NEXT_PUBLIC_SITE_URL: rawSiteUrl,
  });

  if (result.success) {
    return result.data;
  }

  console.warn("Invalid environment variables passed to frontend, falling back to safe defaults:", result.error.format());
  return {
    NEXT_PUBLIC_API_URL: rawApiUrl.startsWith("http") ? rawApiUrl : "http://localhost:8000",
    NEXT_PUBLIC_SITE_URL: rawSiteUrl.startsWith("http") ? rawSiteUrl : "http://localhost:3000",
  };
}

export const env: ClientEnv = getEnv();

