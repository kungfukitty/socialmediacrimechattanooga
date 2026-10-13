/**
 * Shapes for the Hamilton County 9-1-1 public "Active Incidents" list.
 *
 * Column headers as shown on the page (Oct 2026):
 *   Type | Status | Master Incident | Time Created | Agency | Event |
 *   Location (Click Buttons to Locate on Map) | Area
 *
 * Status and type values come from the page's filter controls. Confirm them
 * against the captured fixtures (docs/DATA_SOURCE.md) and update if needed.
 */

export const STATUS_CODES = {
  R: "Reported",
  E: "Enroute",
  OS: "On Scene",
  T: "Transporting",
  H: "At Hospital",
} as const;

export type StatusCode = keyof typeof STATUS_CODES;

export const AGENCY_TYPES = ["Law", "Fire", "EMS", "Road Closure"] as const;
export type AgencyType = (typeof AGENCY_TYPES)[number];

export const AREAS = [
  "Collegedale",
  "Chattanooga",
  "East Ridge",
  "Hamilton County",
  "Red Bank",
  "Signal Mountain",
  "Soddy-Daisy",
] as const;
export type Area = (typeof AREAS)[number];

/** One row exactly as scraped, keyed by column header text. */
export type RawRow = Record<string, string>;

/** A normalized incident, ready for the database. */
export interface Incident {
  /** Master Incident number, used as the primary key. */
  masterIncident: string;
  type: AgencyType | "Unknown";
  /** Raw type text, kept for audit when it doesn't match a known value. */
  typeRaw: string;
  status: StatusCode | "Unknown";
  statusRaw: string;
  /** ISO 8601 timestamp in America/New_York, or null if it could not be parsed. */
  createdAt: string | null;
  createdAtRaw: string;
  agency: string;
  event: string;
  /** Location as published (already block-level on the county page). */
  location: string;
  area: Area | "Unknown";
  areaRaw: string;
}
