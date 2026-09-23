/**
 * Plain-English definitions for every technical term used across the app.
 *
 * Anything jargony — index acronyms, sensor terms, risk levels — should
 * be looked up here so the wording stays consistent on the landing page,
 * the session detail screen, the PDF report, and tooltips.
 */

export type GlossaryEntry = {
  /** Short label as it appears in the UI (NDWI, "Cloud cover", "Risk score"). */
  term: string;
  /** One sentence a non-expert can read in a tooltip. */
  short: string;
  /** Optional second sentence with more detail. */
  detail?: string;
  /** Optional in-app link to a more thorough explanation. */
  link?: string;
};

export const GLOSSARY = {
  // --- Indices --------------------------------------------------------
  ndwi: {
    term: "NDWI",
    short: "Tells us where water actually is in the scene.",
    detail:
      "Built from near-infrared and short-wave infrared light. Values above zero usually mean open water.",
    link: "/methodology",
  },
  mndwi: {
    term: "MNDWI",
    short: "A water-detection signal that holds up better in cities.",
    detail:
      "Same idea as NDWI but uses green light instead of near-infrared so concrete and rooftops don't get mistaken for water.",
    link: "/methodology",
  },
  ndti: {
    term: "NDTI",
    short: "How murky or sediment-loaded the water looks.",
    detail:
      "Higher values mean the water is reflecting more red light, which often comes from suspended sediment.",
    link: "/methodology",
  },
  ndci: {
    term: "NDCI",
    short: "A proxy for chlorophyll — a precursor for algal blooms.",
    detail:
      "Uses the red-edge band that healthy algae reflect strongly. Elevated values are a heads-up, not a confirmed bloom.",
    link: "/methodology",
  },
  ndvi: {
    term: "NDVI",
    short: "How much living vegetation is around the shoreline.",
    detail:
      "Useful as a co-signal: dense or stressed shoreline vegetation often coincides with water-quality changes.",
    link: "/methodology",
  },
  wri: {
    term: "WRI",
    short: "A second water-vs-land moisture signal.",
    detail:
      "Values above ~2.5 strongly suggest open water, complementing NDWI and MNDWI.",
    link: "/methodology",
  },

  // --- Risk -----------------------------------------------------------
  riskScore: {
    term: "Risk score",
    short: "A 0–100 number combining all the indices and field evidence.",
    detail:
      "Calculated by a deterministic formula. Below 33 is Low, 33–66 is Medium, above 66 is High.",
    link: "/methodology",
  },
  riskLow: {
    term: "Low risk",
    short: "Nothing in the data suggests immediate concern.",
    detail: "Keep the routine monitoring cadence and re-image in a couple of weeks.",
  },
  riskMedium: {
    term: "Medium risk",
    short: "One or more indicators are elevated.",
    detail: "Schedule a sampling visit within about a week.",
  },
  riskHigh: {
    term: "High risk",
    short: "Multiple indicators are elevated together.",
    detail: "Send a sampling team within 48 hours and consider alerting the local authority.",
  },
  urgency: {
    term: "Urgency",
    short: "How fast the field team should respond.",
    detail:
      "Routine = next planned visit. Elevated = within a week. Immediate = within 48 hours.",
  },

  // --- Imagery / scene ------------------------------------------------
  sentinel2: {
    term: "Sentinel-2",
    short: "An ESA Earth-observation satellite that revisits each spot every ~5 days.",
    detail:
      "AquaLens uses the L2A surface-reflectance product, which is already corrected for the atmosphere.",
  },
  cloudCover: {
    term: "Cloud cover",
    short: "What percentage of the scene was hidden behind clouds.",
    detail:
      "We pick the most recent scene below the threshold you set. Lower is stricter; many lakes have plenty of clear-sky options at 30%.",
  },
  sceneId: {
    term: "Scene ID",
    short: "A unique identifier for the satellite acquisition we used.",
    detail: "Helpful if you want to cross-reference the imagery in another tool.",
  },
  provider: {
    term: "Provider",
    short: "Where the imagery came from.",
    detail:
      "AquaLens streams Sentinel-2 from Microsoft Planetary Computer (free, no API key).",
  },
  aoi: {
    term: "AOI",
    short: "Area of interest — the polygon we analyse.",
    detail:
      "Click the map and a ~1 km buffer around the pin becomes your AOI. You can also paste GeoJSON for a precise polygon.",
  },
  buffer: {
    term: "Buffer",
    short: "A small box drawn around your pin so we have an area to average over.",
  },
  bandMath: {
    term: "Band math",
    short: "Combining different colour channels of the satellite image with simple formulas.",
  },

  // --- Pipeline -------------------------------------------------------
  fieldEvidence: {
    term: "Field evidence",
    short: "Observations a field team adds (colour, odor, dead fish, recent rain, etc.).",
    detail:
      "Submitting evidence reweights the risk score and refreshes the narrative — it never overrides the satellite-derived numbers.",
  },
  reasoning: {
    term: "Reasoning",
    short: "A plain-English explanation of why the score landed where it did.",
    detail:
      "Generated by Gemini from the deterministic numbers above. The model can only describe; it cannot change the score.",
  },
  limitations: {
    term: "Limitations",
    short: "What this report explicitly is not — including the advisory-only disclaimer.",
  },
} as const satisfies Record<string, GlossaryEntry>;

export type GlossaryKey = keyof typeof GLOSSARY;
