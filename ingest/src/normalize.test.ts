import { describe, expect, it } from "vitest";
import { normalizeRow, parseCreated, parseStatus, RowError } from "./normalize.js";

const header = {
  type: "Type",
  status: "Status",
  id: "Master Incident",
  time: "Time Created",
  agency: "Agency",
  event: "Event",
  loc: "Location (Click Buttons to Locate on Map)",
  area: "Area",
};

describe("normalizeRow", () => {
  it("maps every column of a typical row", () => {
    const inc = normalizeRow({
      [header.type]: "Law",
      [header.status]: "E",
      [header.id]: " 2026-123456 ",
      [header.time]: "10/13/2026 14:05:09",
      [header.agency]: "Chattanooga PD",
      [header.event]: "Burglary",
      [header.loc]: "1200 BLOCK  BOYNTON DR\n",
      [header.area]: "Chattanooga",
    });
    expect(inc).toEqual({
      masterIncident: "2026-123456",
      type: "Law",
      typeRaw: "Law",
      status: "E",
      statusRaw: "E",
      createdAt: "2026-10-13T14:05:09",
      createdAtRaw: "10/13/2026 14:05:09",
      agency: "Chattanooga PD",
      event: "Burglary",
      location: "1200 BLOCK BOYNTON DR",
      area: "Chattanooga",
      areaRaw: "Chattanooga",
    });
  });

  it("keeps unknown values visible instead of dropping them", () => {
    const inc = normalizeRow({ [header.id]: "X1", [header.type]: "Animal", [header.area]: "Ooltewah" });
    expect(inc.type).toBe("Unknown");
    expect(inc.typeRaw).toBe("Animal");
    expect(inc.area).toBe("Unknown");
  });

  it("rejects rows without a Master Incident number", () => {
    expect(() => normalizeRow({ [header.type]: "Law" })).toThrow(RowError);
  });
});

describe("parseStatus", () => {
  it("accepts codes and long labels", () => {
    expect(parseStatus("os")).toBe("OS");
    expect(parseStatus("On Scene")).toBe("OS");
    expect(parseStatus("??")).toBe("Unknown");
  });
});

describe("parseCreated", () => {
  it("handles 12-hour clock", () => {
    expect(parseCreated("10/13/2026 12:15 AM")).toBe("2026-10-13T00:15:00");
    expect(parseCreated("10/13/2026 1:15:30 PM")).toBe("2026-10-13T13:15:30");
  });
  it("returns null on garbage", () => {
    expect(parseCreated("yesterday")).toBeNull();
    expect(parseCreated("")).toBeNull();
  });
});
