import {
  AGENCY_TYPES,
  AREAS,
  STATUS_CODES,
  type AgencyType,
  type Area,
  type Incident,
  type RawRow,
  type StatusCode,
} from "./types.js";

/** Collapse whitespace and trim. Table cells often carry stray newlines and tabs. */
export function clean(value: string | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

/** Find a column by header prefix, so "Location (Click Buttons...)" matches "Location". */
function col(row: RawRow, header: string): string {
  const key = Object.keys(row).find((k) => clean(k).toLowerCase().startsWith(header.toLowerCase()));
  return clean(key ? row[key] : undefined);
}

export function parseStatus(raw: string): StatusCode | "Unknown" {
  const v = clean(raw).toUpperCase();
  if (v in STATUS_CODES) return v as StatusCode;
  // Accept the long form too ("On Scene", "Enroute").
  const match = (Object.entries(STATUS_CODES) as [StatusCode, string][]).find(
    ([, label]) => label.toUpperCase() === v,
  );
  return match ? match[0] : "Unknown";
}

export function parseType(raw: string): AgencyType | "Unknown" {
  const v = clean(raw).toLowerCase();
  return AGENCY_TYPES.find((t) => t.toLowerCase() === v) ?? "Unknown";
}

export function parseArea(raw: string): Area | "Unknown" {
  const v = clean(raw).toLowerCase();
  return AREAS.find((a) => a.toLowerCase() === v) ?? "Unknown";
}

/**
 * Parse "Time Created". The exact format is unconfirmed until fixtures are
 * captured, so this accepts "MM/DD/YYYY HH:MM[:SS] [AM|PM]" and ISO strings.
 * Returns a local (America/New_York) ISO string without an offset, or null.
 */
export function parseCreated(raw: string): string | null {
  const v = clean(raw);
  if (!v) return null;
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(v)) return v;

  const m = v.match(
    /^(\d{1,2})\/(\d{1,2})\/(\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?$/i,
  );
  if (!m) return null;
  const [, mo, d, y, hRaw, min, s = "00", ampm] = m;
  let h = Number(hRaw);
  if (ampm) {
    const pm = ampm.toUpperCase() === "PM";
    if (h === 12) h = pm ? 12 : 0;
    else if (pm) h += 12;
  }
  if (h > 23) return null;
  const pad = (n: string | number) => String(n).padStart(2, "0");
  return `${y}-${pad(mo!)}-${pad(d!)}T${pad(h)}:${min}:${s}`;
}

export class RowError extends Error {}

/** Normalize one scraped row. Throws RowError if the primary key is missing. */
export function normalizeRow(row: RawRow): Incident {
  const masterIncident = col(row, "Master Incident");
  if (!masterIncident) throw new RowError("Row has no Master Incident number");

  const typeRaw = col(row, "Type");
  const statusRaw = col(row, "Status");
  const createdAtRaw = col(row, "Time Created");
  const areaRaw = col(row, "Area");

  return {
    masterIncident,
    type: parseType(typeRaw),
    typeRaw,
    status: parseStatus(statusRaw),
    statusRaw,
    createdAt: parseCreated(createdAtRaw),
    createdAtRaw,
    agency: col(row, "Agency"),
    event: col(row, "Event"),
    location: col(row, "Location"),
    area: parseArea(areaRaw),
    areaRaw,
  };
}
