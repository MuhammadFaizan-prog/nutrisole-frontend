// G9 Stage J5: what the debug overlay draws on the preview. Boxes carry a class NAME only: never a score, percentage or grade.
import type { Size } from '../pipeline/camera.ts';
import type { Detection } from '../pipeline/tracker.ts';
import type { StillCropPlan } from '../pipeline/camera.ts';
import { stillBoxToView } from './orientation.ts';
import { labelOf } from './debugPipeline.ts';

export type OverlayBox = { left: number; top: number; width: number; height: number; label: string; kind: 'detection' | 'crop' };

export function overlayBoxes(dets: Detection[], plan: StillCropPlan | null, still: Size, view: Size): OverlayBox[] {
  const out: OverlayBox[] = dets.map((d) => ({ ...stillBoxToView(d.box, still, view), label: labelOf(d.classId), kind: 'detection' as const }));
  if (plan) out.push({ ...stillBoxToView([plan.crop.x, plan.crop.y, plan.crop.x + plan.crop.w, plan.crop.y + plan.crop.h], still, view), label: 'crop', kind: 'crop' });
  return out.filter((b) => b.width > 0 && b.height > 0);
}
