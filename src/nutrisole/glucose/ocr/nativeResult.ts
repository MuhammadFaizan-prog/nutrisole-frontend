import { boxesToRows } from './layout';
import type { OcrResult } from '../import/fileImport';

export type NativeCaptureBox = { text: string; x: number; y: number; width: number; height: number; angle: number; confidence: number | null };
export type NativeCaptureResult = { engine: string; durationMs: number; pages: { page: number; boxes: NativeCaptureBox[] }[] };

export function nativeCaptureResult(result: NativeCaptureResult): OcrResult {
  const boxes = result.pages.flatMap(p => p.boxes);
  const known = boxes.filter(b => b.confidence !== null);
  const weight = known.reduce((n, b) => n + b.text.length, 0);
  return {
    engine: result.engine, durationMs: Math.round(result.durationMs),
    confidence: known.length === boxes.length && weight ? known.reduce((n, b) => n + b.confidence! * b.text.length, 0) / weight : null,
    lines: result.pages.flatMap(p => boxesToRows(p.boxes.filter(b => b.width > 0 && b.height > 0).map(b => ({ text: b.text, cx: b.x + b.width / 2, cy: b.y + b.height / 2, w: b.width, h: b.height, angle: b.angle, confidence: b.confidence ?? 0.5, poly: [] }))).map(l => ({ ...l, locator: `page ${p.page} ${l.locator}` }))),
  };
}
