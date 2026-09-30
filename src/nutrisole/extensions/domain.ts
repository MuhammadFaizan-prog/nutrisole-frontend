import type { ExpansionState, Reading } from './model';
import { foodInfo } from './model';
export function accountError(s: ExpansionState, action: string): string | undefined {
  if (action === 'create-account' && !(s.fields.name || '').trim()) return 'Enter your name.';
  if (action !== 'reset-password' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s.fields.email || '')) return 'Enter a valid email address.';
  if (action === 'recover') return;
  const password = s.fields[action === 'reset-password' ? 'newPassword' : 'password'] || '';
  if (password.length < 8) return 'Use at least 8 characters for your password.';
  if (action === 'reset-password' && password !== s.fields.confirmPassword) return 'The passwords do not match.';
  if (action === 'create-account' && !s.toggles.terms) return 'Please review and accept the Terms and Privacy Policy.';
}
export function readingResult(s: ExpansionState): { error?: string; record?: Reading } {
  const raw = (s.fields.reading || '').trim();
  if (!/^\d+(\.\d+)?$/.test(raw) || Number(raw) <= 0) return { error: 'Enter a positive numeric meter reading.' };
  if (!Number.isFinite(Number(raw)) || raw.length > 8) return { error: 'Check the value against your meter.' };
  const unit = s.choices.unit; const limit = unit === 'mg/dL' ? 1000 : 55.5;
  if (Number(raw) > limit) return { error: 'This value is outside the demo entry range. Check the value and unit on your meter.' };
  if (!validMeasurementDate(s.choices.date)) return { error: 'Enter a valid measurement date, such as Sep 30, 2026.' };
  if (!/^(0?[1-9]|1[0-2]):[0-5]\d (AM|PM)$/.test(s.choices.time)) return { error: 'Enter a valid time, such as 8:15 AM.' };
  const record = { id: s.currentReading?.id || `manual-${s.readings.length + 1}`, value: Number(raw), unit, date: s.choices.date, time: s.choices.time, context: s.choices.context, source: 'Manual entry' };
  if (s.readings.some(r => r.id !== record.id && r.date === record.date && r.time === record.time && r.value === record.value && r.unit === record.unit)) return { error: 'This manual reading is already in your history.' };
  return { record };
}
export function validMeasurementDate(value: string) {
  const match = /^([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$/.exec(value); if (!match) return false;
  const month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].indexOf(match[1]); const day = Number(match[2]); const year = Number(match[3]);
  if (month < 0 || year < 1900) return false; const date = new Date(Date.UTC(year, month, day)); return date.getUTCMonth() === month && date.getUTCDate() === day;
}
export function saveReading(s: ExpansionState, record: Reading): ExpansionState { return { ...s, readings: [...s.readings.filter(r => r.id !== record.id), record], currentReading: record, readingRemoved: false }; }
export function mealResult(s: ExpansionState, draft: boolean) {
  const food = s.choices.food; const info = foodInfo(food); const byWeight = s.choices.portion === 'By weight';
  const amount = Number(s.fields[byWeight ? 'grams' : 'amount'] || (byWeight ? info.grams : 1));
  if (!Number.isFinite(amount) || amount <= 0 || amount > (byWeight ? 5000 : 30)) return { error: byWeight ? 'Enter an edible weight between 0 and 5,000 g.' : 'Enter an amount between 0 and 30.' };
  const factor = s.choices.portion === 'By size' ? { small: .75, medium: 1, large: 1.25 }[s.choices.size as 'small' | 'medium' | 'large'] || 1 : 1;
  const grams = byWeight ? amount : amount * info.grams * factor;
  return { meal: { food, grams, calories: Math.round(info.calories * grams / 100), draft } };
}
export function assistantReply(question: string): string {
  if (/insulin|dosage|dose|medicin|diagnos/i.test(question)) return 'I cannot diagnose or recommend\nmedicines or insulin doses.\nPlease ask a qualified clinician.\n\nI can explain how to use NutriSole\nor discuss everyday food choices.';
  if (/plan|allerg/i.test(question)) return 'Review your dietary preferences\nand declared allergens before\ncreating your weekly plan.\n\nOpen “Why this plan?” to see\nthe profile and data window used.';
  return 'Try adding a mix of foods that\nfits your preferences. Confirm\nthe food and portion before logging.\n\nThis is a general demo response.\nNo external health data was used.';
}
