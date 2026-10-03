export type Insets = { top: number; right: number; bottom: number; left: number };
export function viewport(width: number, height: number, insets: Insets) {
  const usableWidth = Math.max(0, width - insets.left - insets.right);
  return { width: usableWidth, height: Math.max(0, height - insets.top - insets.bottom), gutter: usableWidth < 360 ? 16 : 20, compact: usableWidth < 380 };
}
export function typography(_width: number, _height: number) {
  return { body: 16, title: 24 };
}
export function largeTextLayout(width: number, fontScale: number) {
  const expanded = fontScale > 1.6;
  return { expanded, navigationColumns: expanded ? 3 : 5, brandSize: expanded && width < 380 ? 24 : 32 };
}
/** Keep the reference two-card layout only while each label has usable text space. */
export function homeActionsLayout(availableWidth: number, fontScale: number) {
  const padding = availableWidth < 340 ? 14 : 18;
  const textWidth = (availableWidth - 8) / 2 - padding * 2 - 16;
  return { columns: textWidth >= 108 * fontScale ? 2 : 1, padding };
}
/** Enlarged weekday text gets horizontal space, never a second calendar row. */
export function weekStripLayout(availableWidth: number, count: number, fontScale: number) {
  const gap = 3;
  const fitted = Math.max(0, (availableWidth - gap * (count - 1)) / count);
  const minimum = 32 * fontScale + 4;
  return { gap, cellWidth: Math.max(fitted, minimum), scroll: fitted < minimum };
}
export function cameraFrameHeight(previewHeight: number, frameWidth: number, occupied: number) { return Math.max(72, Math.min(frameWidth, previewHeight - occupied)); }
export function cameraNeedsScroll(previewHeight: number, occupied: number) { return occupied + 72 > previewHeight; }
