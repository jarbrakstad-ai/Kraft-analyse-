/** Pivot an array of {timestamp_utc, [groupKey]: string, [valueKey]: number} into wide rows keyed by group value. */
export function pivotByTimestamp<T extends { timestamp_utc: string }>(
  rows: T[],
  groupKey: string,
  valueKey: string,
): Record<string, string | number>[] {
  const byTimestamp = new Map<string, Record<string, string | number>>();
  for (const row of rows) {
    const asRecord = row as unknown as Record<string, unknown>;
    const ts = row.timestamp_utc;
    const group = String(asRecord[groupKey]);
    const value = asRecord[valueKey] as number;
    if (!byTimestamp.has(ts)) byTimestamp.set(ts, { timestamp_utc: ts });
    byTimestamp.get(ts)![group] = value;
  }
  return Array.from(byTimestamp.values()).sort((a, b) => String(a.timestamp_utc).localeCompare(String(b.timestamp_utc)));
}

export function formatTimeAxis(isoTimestamp: string): string {
  const d = new Date(isoTimestamp);
  return d.toLocaleString("no-NO", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function formatDateAxis(isoTimestamp: string): string {
  const d = new Date(isoTimestamp);
  return d.toLocaleDateString("no-NO", { day: "2-digit", month: "2-digit" });
}

export function formatR(r: number | null): string {
  if (r === null) return "—";
  return r.toFixed(3);
}

/** Safe numeric formatter for recharts Tooltip formatter/labelFormatter callbacks, whose value may be undefined/non-numeric. */
export function formatNumber(value: unknown, digits = 1): string {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : String(value ?? "");
}

export function formatDateTimeLabel(value: unknown): string {
  if (typeof value !== "string" && typeof value !== "number") return "";
  return new Date(value).toLocaleString("no-NO");
}

export function formatDateLabel(value: unknown): string {
  if (typeof value !== "string" && typeof value !== "number") return "";
  return new Date(value).toLocaleDateString("no-NO");
}
