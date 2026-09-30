import { useState } from 'react';
import { initialExpansionState, type ExpansionState, type Reading } from './model';
import { accountError, assistantReply, mealResult, readingResult, saveReading, validMeasurementDate } from './domain';
import type { AppRoute, Sheet } from '../types';
export function useExpansion() {
  const [state, setState] = useState(initialExpansionState);
  const update = (patch: Partial<ExpansionState>) => setState(s => ({ ...s, ...patch }));
  const field = (key: string, value: string) => setState(s => ({ ...s, fields: { ...s.fields, [key]: value } }));
  function action(action: string, go: (r: AppRoute) => void, back: () => void, open: (s: Sheet) => void) {
    const s = state;
    const notice = (title: string, description: string, choices?: Sheet['choices']) => open({ title, description, choices });
    const choose = (title: string, key: string, options: string[]) => open({ title, choices: options.map(label => ({ label, selected: s.choices[key] === label, action: () => setState(v => ({ ...v, choices: { ...v.choices, [key]: label } })) })) });
    const edit = (title: string, key: string, value: string, validate?: (v: string) => string | undefined, destination: 'fields' | 'choices' = 'fields') => open({ title, fields: [{ key, label: title, value }], save: v => { const error = validate?.(v[key]); if (error) return error; setState(old => ({ ...old, [destination]: { ...old[destination], [key]: v[key] } })); } });
    if (action === 'back') return back();
    if (action.startsWith('go:')) return go(action.slice(3) as AppRoute);
    if (action.startsWith('toggle:')) { const key = action.slice(7); return setState(v => ({ ...v, toggles: { ...v.toggles, [key]: !v.toggles[key] } })); }
    if (action.startsWith('choose:')) { const [, key, ...parts] = action.split(':'); return setState(v => ({ ...v, choices: { ...v.choices, [key]: parts.join(':') } })); }
    if (['sign-in', 'create-account', 'recover', 'reset-password'].includes(action)) {
      const error = accountError(s, action); if (error) return notice('Check your details', error);
      if (action === 'recover') return notice('Check your inbox', 'If an account exists, a recovery link would be sent. This frontend sends no email.', [{ label: 'Preview recovery link', action: () => go('reset-password') }, { label: 'Back to sign in', action: () => go('sign-in') }]);
      setState(v => ({ ...v, session: action === 'sign-in', fields: { ...v.fields, password: '', newPassword: '', confirmPassword: '' } }));
      if (action === 'sign-in') return notice('Frontend demo', 'Account validation is simulated. No account or password is stored.', [{ label: 'Continue to NutriSole', action: () => go('flow-directory') }]);
      return go(action === 'create-account' ? 'verify-email' : 'sign-in');
    }
    switch (action) {
      case 'terms': return notice('Terms & Privacy', 'This local frontend uses synthetic records and keeps new entries in memory for this session. No account, health-provider connection or external processing is created.');
      case 'resend': return notice('Resend link', 'No email is sent in this frontend demo. Preview the verification flow below.', [{ label: 'Preview verified link', action: () => go('sign-in') }, { label: 'Preview expired link', action: () => notice('Link expired', 'Request a fresh verification link or use another email.') }]);
      case 'verify-demo': return notice('Verification preview', 'A real email application is not connected. Choose a demo link state.', [{ label: 'Valid link · Continue', action: () => go('sign-in') }, { label: 'Expired link', action: () => notice('Link expired', 'Return and choose Resend link.') }]);
      case 'evidence': return notice('Assessment evidence', 'Sample visible colour: even red. Shape: whole apple. Surface: minor marks. Confidence: 97%. Model v1.0 · Rubric v1.0. The original prediction stays Apple even if you choose another food. A photo cannot determine food safety.', [{ label: 'Correct food label', action: () => go('food-selector') }, { label: 'Report assessment', action: () => go('report-output') }]);
      case 'market': return choose('Choose a market', 'market', ['Local retail · Demo', 'Wholesale · Demo', 'Online · Demo']);
      case 'unit-market': return notice('Market comparison unit', 'Per kg is the comparison unit for this demo entry. No verified market observations are available.');
      case 'choose-photo': return notice('Choose a sample photo', 'This frontend previews upload outcomes without uploading a file.', [{ label: 'Clear single apple · Review', action: () => go('analysis-result') }, { label: 'Blurred photo · Try again', action: () => go('capture-retry') }, { label: 'Multiple items', action: () => notice('Frame one item', 'Select one supported produce item before retrying.') }, { label: 'Unsupported or corrupt file', action: () => notice('Cannot use this photo', 'Use a supported image below 10 MB and try again.') }]);
      case 'basis': return choose('Nutrition basis', 'basis', ['per 100 g', 'per medium']);
      case 'catalog-source': return notice('Demo catalog v1', 'These synthetic fixtures reproduce the supplied UI concepts. They are not a verified food-composition database. Preparation is Raw. No verified source date is available.');
      case 'reading-unit': return choose('Display unit', 'unit', ['mg/dL', 'mmol/L']);
      case 'manual-source': return notice('Manual meter entry', 'NutriSole does not measure glucose. Enter values already measured by your meter.');
      case 'new-reading': setState(v => ({ ...v, currentReading: null, readingRemoved: false, fields: { ...v.fields, reading: '' } })); return go('add-reading');
      case 'reading-date': return edit('Measured on', 'date', s.choices.date, v => validMeasurementDate(v) ? undefined : 'Use a date such as Sep 30, 2026.', 'choices');
      case 'reading-time': return edit('Time', 'time', s.choices.time, v => /^(0?[1-9]|1[0-2]):[0-5]\d (AM|PM)$/.test(v) ? undefined : 'Use a time such as 8:15 AM.', 'choices');
      case 'reading-context': return choose('Measurement context', 'context', ['Before a meal', 'After a meal', 'Fasting', 'Other']);
      case 'review-reading': { const result = readingResult(s); if (result.error || !result.record) return notice('Check reading', result.error || 'Reading is missing.'); const record = result.record; return notice('Review manual reading', `${record.value} ${record.unit}\n${record.date} · ${record.time} · Pacific Time\n${record.context}\nSource: manual entry`, [{ label: 'Confirm & save reading', action: () => { setState(v => saveReading(v, record)); go('reading-detail'); } }]); }
      case 'latest-reading': update({ currentReading: s.readings.at(-1) || null }); return go('reading-detail');
      case 'edit-reading': { const r: Reading = s.currentReading || { id: 'sample-edit', value: 110, unit: 'mg/dL', date: 'Sep 30, 2026', time: '8:15 AM', context: 'Before a meal', source: 'Manual entry' }; setState(v => ({ ...v, currentReading: r, choices: { ...v.choices, unit: r.unit, date: r.date, time: r.time, context: r.context }, fields: { ...v.fields, reading: String(r.value) } })); return go('add-reading'); }
      case 'remove-reading': return notice('Remove manual record?', 'Remove this record from the new frontend session. The six original screens are unaffected.', [{ label: 'Remove record', action: () => setState(v => ({ ...v, readings: v.readings.filter(r => r.id !== v.currentReading?.id), currentReading: null, readingRemoved: true })) }]);
      case 'provider-info': return notice('Apple Health', 'A native provider is not connected in this frontend demo. Manual entry remains available.');
      case 'permissions': return notice('Review requested permissions', `Glucose readings: ${s.toggles.shareGlucose ? 'requested' : 'off'}\nActivity records: ${s.toggles.shareActivity ? 'requested' : 'off'}\nHealth import consent: ${s.toggles.healthImport ? 'on' : 'off'}\nNo OS permissions will be requested by this demo.`, [{ label: 'Preview provider unavailable', action: () => notice('Provider unavailable', 'Apple Health is not connected. No records imported. Continue with manual entry.', [{ label: 'Add reading manually', action: () => go('add-reading') }]) }, { label: 'Review consent', action: () => go('privacy-data-rights') }]);
      case 'profile-diet': return notice('Recorded dietary preferences', 'Balanced, higher protein. The new frontend reads a sample profile; the original profile is preserved.');
      case 'profile-allergens': return notice('Declared allergens', 'Tree nuts and shellfish. Check actual ingredients before following any meal suggestion.');
      case 'profile-activity': return notice('Recorded activity preferences', 'Strength training, 3–4 days/week. Review foot and mobility answers before activity suggestions.', [{ label: 'Review foot support', action: () => go('foot-questionnaire') }]);
      case 'plan-week': return notice('Plan week', 'Monday Sep 28 – Sunday Oct 4, 2026. This frontend uses the reviewed concept week.');
      case 'plan-window': return notice('Plan input window', 'Last 7 days. Profile preferences, declared allergens and activity are sample inputs. No provider glucose data is used.');
      case 'create-plan': if (s.choices.comfort === 'Concern' || s.choices.mobility === 'Limited') return notice('Activity deferred', 'The recorded concern needs a qualified assessment. Meal planning can continue with your recorded preferences.', [{ label: 'Review sample meal plan', action: () => { update({ planVersion: s.planVersion + 1 }); go('plan-rationale'); } }, { label: 'Review foot guidance', action: () => go('foot-guidance') }]); update({ planVersion: s.planVersion + 1 }); return go('plan-rationale');
      case 'complete-activity': if (s.choices.comfort === 'Concern' || s.choices.mobility === 'Limited') return notice('Activity deferred', 'Seek a qualified assessment before following the movement suggestion.'); return update({ activityComplete: !s.activityComplete });
      case 'substitute-activity': if (s.choices.comfort === 'Concern' || s.choices.mobility === 'Limited') return notice('No compatible substitute', 'Activity remains deferred while the recorded concern needs assessment.'); return choose('Choose a sample activity', 'activity', ['Gentle movement', 'Comfortable stretching']);
      case 'review-foot': return notice('Review your answers', `Shoe fit: ${s.choices.fit}\nComfort: ${s.choices.comfort}\nMobility: ${s.choices.mobility}\nRule set v1 · General information only.`, [{ label: 'See general guidance', action: () => go('foot-guidance') }]);
      case 'fit-tip': return notice('Comfortable fit', 'Allow enough room around the toes, use a secure fit, and review comfort while wearing footwear. This is general guidance.');
      case 'comfort-tip': return notice('Changes in comfort', 'Review changes in footwear or routine. If pain or a concern persists, seek a qualified assessment.');
      case 'assistant-food': field('assistantResponse', assistantReply('food')); return;
      case 'assistant-plan': field('assistantResponse', assistantReply('plan')); return;
      case 'assistant-send': if (!(s.fields.assistantQuestion || '').trim()) return notice('Enter a question', 'Ask about food, everyday activity or using NutriSole.'); setState(v => ({ ...v, fields: { ...v.fields, assistantResponse: assistantReply(v.fields.assistantQuestion), assistantQuestion: '' } })); return;
      case 'assistant-sources': return notice('Response sources', 'No external source was retrieved. This is a scripted frontend response using the sample profile and NutriSole flow information.');
      case 'export': return notice('Export new demo records', 'The export covers entries from the added flows in this frontend session. It does not include real health-provider data or the six original screen fixtures.', [{ label: 'Prepare export', action: () => { update({ exportStatus: 'Demo export ready' }); open({ title: 'Demo export · JSON', description: 'Copy these session records. No file is sent anywhere.', fields: [{ key: 'json', label: 'Session export', value: JSON.stringify({ readings: s.readings, meals: s.meals, report: s.reportSubmitted ? { id: 'DEMO-104', reason: s.choices.reason } : null }, null, 2), multiline: true }] }); } }]);
      case 'retained': return notice('Retained records', `New session: ${s.readings.length} meter readings, ${s.meals.length} meal entries. Food photo retention: ${s.toggles.retainPhotos ? 'enabled in preferences' : 'off'}. No original photos are captured by this demo.`, [{ label: 'Clear new session records', action: () => update({ readings: [], currentReading: null, meals: [] }) }]);
      case 'delete-account': return open({ title: 'Confirm demo deletion', description: 'No server account exists. Enter DELETE to clear the added flow session only. Original screens and their saved demo stay untouched.', fields: [{ key: 'confirm', label: 'Type DELETE', value: '' }], save: values => { if (values.confirm !== 'DELETE') return 'Type DELETE to confirm.'; setState(initialExpansionState()); go('sign-in'); } });
      case 'save-preferences': return notice('Preferences saved for this session', 'No provider data, photos or assistant context is imported by this frontend.', [{ label: 'Review reminders', action: () => go('reminders') }, { label: 'Explore all flows', action: () => go('flow-directory') }]);
      case 'quiet-hours': return edit('Quiet hours', 'quietHours', s.fields.quietHours || '10:00 PM – 7:00 AM');
      case 'reminder-zone': return edit('Time zone', 'reminderZone', s.fields.reminderZone || 'Pacific Time');
      case 'notification-permission': return notice('Notifications are not enabled', 'This frontend does not schedule or send OS notifications. Your selected reminders remain inactive.');
      case 'save-reminders': return notice('Reminder preferences saved', 'Saved in the added flow session. Notifications remain inactive until a real provider is connected.');
      case 'review-report': if (s.reportSubmitted) return notice('Report already submitted', 'DEMO-104 is already recorded in this session.', [{ label: 'View report', action: () => go('report-status') }]); return notice('Review shared report', `Output: ANALYSIS-DEMO-17\nReason: ${s.choices.reason}\nDetails: ${s.fields.reportDetails || 'None'}\nNo health history or photo is attached.`, [{ label: 'Submit demo report', action: () => { update({ reportSubmitted: true }); go('report-status'); } }]);
      case 'history-window': return notice('History window', 'Thursday Sep 24 – Wednesday Sep 30, 2026. The original UI fixtures keep their original dates.');
      case 'history-filter': return choose('Filter records', 'history', ['All', 'Food', 'Meals', 'Plans']);
      case 'catalog-source-edit': return edit('Source reference', 'catalogSource', s.fields.catalogSource || '');
      case 'catalog-date': return edit('Observation date', 'observationDate', s.fields.observationDate || '', v => !Number.isNaN(Date.parse(v)) ? undefined : 'Enter a valid observation date.');
      case 'catalog-form': return notice('Food form', 'Raw. A prepared food must use a separate catalog record.');
      case 'catalog-grade': return notice('Grade applicability', 'Pending curator evidence. Verification requires a real source and grade rubric.');
      case 'catalog-save': return notice('Draft review saved', 'The draft remains unpublished. Source verification and observation evidence are still required.');
      case 'catalog-reject': return notice('Reject this draft?', 'A rejection reason is required in the sample curator workflow.', [{ label: 'Add rejection reason', action: () => open({ title: 'Rejection reason', fields: [{ key: 'reason', label: 'Reason', value: '', multiline: true }], save: v => (v.reason || '').trim() ? undefined : 'Enter a reason before rejecting.' }) }]);
      case 'catalog-publish': return notice('Publishing blocked', 'Verification gates are incomplete.');
      case 'release-evidence': return notice('Release evidence · Sample', 'Manifest: present\nDataset licence: review needed\nClass thresholds: review needed\nSafety regression: pending\nCandidate v1.1 remains inactive. No model is executed or installed by this frontend.');
      case 'activate-package': return notice('Activation blocked', 'The sample licence, threshold and safety gates have not passed.');
      case 'rollback': return notice('Rollback history', 'Active sample package: v1.0. No earlier verified package is available. A real rollback requires verified evidence and administrator confirmation.');
      case 'audit-date': return edit('Audit date', 'auditDate', s.fields.auditDate || 'Sep 30, 2026');
      case 'audit-category': return choose('Event category', 'auditCategory', ['All events', 'Success', 'Denied']);
      case 'filter-audit': return notice('Audit filter applied', `${s.choices.auditCategory || 'All events'} · ${s.fields.auditDate || 'Sep 30, 2026'}. Sample redacted metadata only.`);
      case 'triage-save': update({ reportResolved: s.choices.triage === 'Resolved' }); return notice('Sample review saved', `DEMO-104 · ${s.choices.triage}\nThe original analysis evidence is retained. No report is sent to a real support service.`, [{ label: 'View report status', action: () => go('report-status') }]);
      case 'portion-size': return choose('Portion size', 'size', ['small', 'medium', 'large']);
      case 'amount-minus': field('amount', String(Math.max(.5, Number(s.fields.amount || 1) - .5))); return;
      case 'amount-plus': field('amount', String(Math.min(30, Number(s.fields.amount || 1) + .5))); return;
      case 'save-meal': case 'draft-meal': { const result = mealResult(s, action === 'draft-meal'); if (!result.meal) return notice('Check portion', result.error || 'Enter a valid portion.'); const meal = result.meal; return notice(meal.draft ? 'Save this draft?' : 'Confirm meal', `${meal.food} · ${Math.round(meal.grams)} g · ≈ ${meal.calories} cal\n${meal.draft ? 'Drafts are not marked as consumed.' : 'Values are sample estimates.'}`, [{ label: meal.draft ? 'Save draft' : 'Log confirmed meal', action: () => { setState(v => ({ ...v, meals: [...v.meals, meal] })); go('personal-history'); } }]); }
      case 'staff-workspace': return notice('Staff preview workspace', 'Select a role to preview synthetic staff flows. This frontend does not grant permissions or access production records.', [{ label: 'Catalog curator', action: () => go('catalog-queue') }, { label: 'Model administrator', action: () => go('model-release') }, { label: 'Operations administrator', action: () => go('operations-audit') }, { label: 'Support curator', action: () => go('report-triage') }]);
      default: if (action.startsWith('audit-detail:')) return notice(action.slice(13), 'Sample audit event. Metadata only: actor role, event outcome, request ID and time. No health payload or credentials are exposed.');
    }
  }
  return { state, field, action, reset: () => setState(initialExpansionState()) };
}
