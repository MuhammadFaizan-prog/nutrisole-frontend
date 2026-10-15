import type { ExpansionState } from './model';
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
// Glucose validation lives in ../glucose/validation.ts (single domain boundary for manual entry and imports).
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
