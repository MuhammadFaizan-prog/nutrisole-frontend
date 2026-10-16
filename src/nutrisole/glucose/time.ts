// Wall-clock ↔ instant helpers. The existing UI shows dates as "Oct 16, 2026" and
// times as "8:15 AM"; readings store the UTC instant plus the offset of the wall clock
// where they were taken so history renders the meter's local time anywhere.

const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export type WallClock = { year: number; month: number; day: number; hour: number; minute: number };

export function parseDisplayDate(value: string): { year: number; month: number; day: number } | null {
  const match = /^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$/.exec(value.trim());
  if (!match) return null;
  const month = months.indexOf(match[1]); const day = Number(match[2]); const year = Number(match[3]);
  if (month < 0 || year < 2000 || year > 2100) return null;
  const probe = new Date(Date.UTC(year, month, day));
  if (probe.getUTCMonth() !== month || probe.getUTCDate() !== day) return null;
  return { year, month, day };
}

export function parseDisplayTime(value: string): { hour: number; minute: number } | null {
  const match = /^(0?[1-9]|1[0-2]):([0-5]\d) (AM|PM)$/.exec(value.trim());
  if (!match) return null;
  const h12 = Number(match[1]) % 12;
  return { hour: match[3] === 'PM' ? h12 + 12 : h12, minute: Number(match[2]) };
}

/** Device offset (minutes east of UTC) in effect at the given wall clock. */
export function deviceOffsetMinutes(clock: WallClock): number {
  const local = new Date(clock.year, clock.month, clock.day, clock.hour, clock.minute);
  return -local.getTimezoneOffset();
}

export function deviceTimeZoneName(): string | null {
  try { return Intl.DateTimeFormat().resolvedOptions().timeZone || null; } catch { return null; }
}

/** UTC ISO instant for a wall clock at a fixed offset. */
export function wallClockToInstant(clock: WallClock, offsetMinutes: number): string {
  const ms = Date.UTC(clock.year, clock.month, clock.day, clock.hour, clock.minute) - offsetMinutes * 60_000;
  return new Date(ms).toISOString();
}

/** Wall clock of an instant viewed at a fixed offset. */
export function instantToWallClock(iso: string, offsetMinutes: number): WallClock {
  const shifted = new Date(Date.parse(iso) + offsetMinutes * 60_000);
  return { year: shifted.getUTCFullYear(), month: shifted.getUTCMonth(), day: shifted.getUTCDate(), hour: shifted.getUTCHours(), minute: shifted.getUTCMinutes() };
}

export function formatDisplayDate(c: { year: number; month: number; day: number }) { return `${months[c.month]} ${c.day}, ${c.year}`; }
export function formatDisplayTime(c: { hour: number; minute: number }) {
  const h = c.hour % 12 || 12; return `${h}:${String(c.minute).padStart(2, '0')} ${c.hour < 12 ? 'AM' : 'PM'}`;
}
export function formatOffset(offsetMinutes: number) {
  const sign = offsetMinutes < 0 ? '−' : '+'; const abs = Math.abs(offsetMinutes);
  return `UTC${sign}${String(Math.floor(abs / 60)).padStart(2, '0')}:${String(abs % 60).padStart(2, '0')}`;
}
export function timeZoneLabel(name: string | null, offsetMinutes: number) { return name ? `${name} (${formatOffset(offsetMinutes)})` : `Device time (${formatOffset(offsetMinutes)})`; }

/** Current device wall clock as the UI strings. */
export function nowDisplay(now = new Date()) {
  const clock = { year: now.getFullYear(), month: now.getMonth(), day: now.getDate(), hour: now.getHours(), minute: now.getMinutes() };
  return { date: formatDisplayDate(clock), time: formatDisplayTime(clock) };
}

/** Stable chronological order: measuredAt, then createdAt, then id. */
export function compareChronological(a: { measuredAt: string; createdAt: string; id: string }, b: { measuredAt: string; createdAt: string; id: string }) {
  return Date.parse(a.measuredAt) - Date.parse(b.measuredAt) || Date.parse(a.createdAt) - Date.parse(b.createdAt) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
}
