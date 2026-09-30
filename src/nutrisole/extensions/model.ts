// App-owned layers shared by React Native and the editable Figma importer.
// Coordinates describe the selected 393 × 852 concepts; images are discrete photos only.
export const extensionRoutes = ['sign-in', 'create-account', 'verify-email', 'recover-account', 'reset-password', 'analysis-result', 'market-reference', 'capture-retry', 'food-selector', 'nutrition-details', 'glucose-overview', 'add-reading', 'reading-detail', 'health-connections', 'plan-generation', 'activity-plan', 'plan-rationale', 'foot-questionnaire', 'foot-guidance', 'assistant', 'privacy-data-rights', 'reminders', 'report-output', 'report-status', 'personal-history', 'catalog-queue', 'catalog-review', 'model-release', 'operations-audit', 'report-triage', 'flow-directory', 'portion-confirmation'] as const;
export type ExtensionRoute = typeof extensionRoutes[number];
export type Layer = {
  kind: 'text' | 'surface' | 'photo' | 'icon' | 'button' | 'input' | 'toggle' | 'radio';
  x: number; y: number; w: number; h: number; text?: string; size?: number; line?: number;
  color?: string; fill?: string; radius?: number; bold?: boolean; serif?: boolean;
  align?: 'left' | 'center' | 'right'; asset?: string; icon?: string; action?: string;
  field?: string; value?: string; placeholder?: string; secure?: boolean; numeric?: boolean;
  multiline?: boolean; selected?: boolean; disabled?: boolean; maxLength?: number; leadingIcon?: string; stroke?: string; strokeWidth?: number;
};
export type Scene = { id: ExtensionRoute; title: string; role: string; layers: Layer[]; height: number };
export type Reading = { id: string; value: number; unit: string; date: string; time: string; context: string; source: string };
export type ExpansionState = {
  fields: Record<string, string>; choices: Record<string, string>; toggles: Record<string, boolean>;
  readings: Reading[]; currentReading: Reading | null; readingRemoved: boolean;
  planVersion: number; activityComplete: boolean; reportSubmitted: boolean; reportResolved: boolean;
  exportStatus: string; session: boolean; meals: { food: string; grams: number; calories: number; draft: boolean }[];
};
export function initialExpansionState(): ExpansionState {
  return { fields: {}, choices: { food: 'Apple', unit: 'mg/dL', date: 'Sep 30, 2026', time: '8:15 AM', context: 'Before a meal', basis: 'per 100 g', fit: 'Comfortable', comfort: 'No concern', mobility: 'Unrestricted', history: 'All', catalog: 'Pending', reason: 'Wrong food', triage: 'In review', day: 'Wed', portion: 'By amount', size: 'medium' }, toggles: {}, readings: [], currentReading: null, readingRemoved: false, planVersion: 1, activityComplete: false, reportSubmitted: false, reportResolved: false, exportStatus: 'No export requested', session: false, meals: [] };
}
export const colors = { cream: '#faf8f1', green: '#123f2c', ink: '#080d16', muted: '#5c626d', border: '#ebe7df', pale: '#eaf3e8', card: '#fffdf9' };
const foods: Record<string, { calories: number; carbs: string; protein: string; fat: string; fibre: string; grams: number; asset: string }> = {
  Apple: { calories: 52, carbs: '13.8', protein: '0.3', fat: '0.2', fibre: '2.4', grams: 182, asset: 'apple-thumbnail' },
  Banana: { calories: 89, carbs: '22.8', protein: '1.1', fat: '0.3', fibre: '2.6', grams: 118, asset: 'extension-banana' },
  Tomato: { calories: 18, carbs: '3.9', protein: '0.9', fat: '0.2', fibre: '1.2', grams: 123, asset: 'extension-tomato' },
};
export function foodInfo(name: string) { return foods[name] || foods.Apple; }
export function buildScene(id: ExtensionRoute, s = initialExpansionState()): Scene {
  const layers: Layer[] = [];
  const scene: Scene = { id, title: id.replaceAll('-', ' '), role: ['catalog-queue', 'catalog-review', 'model-release', 'operations-audit', 'report-triage'].includes(id) ? 'staff' : 'consumer', height: 852, layers };
  const add = (kind: Layer['kind'], x: number, y: number, w: number, h: number, extra: Partial<Layer> = {}) => layers.push({ kind, x, y, w, h, ...extra });
  const text = (value: string, x: number, y: number, w = 345, size = 16, extra: Partial<Layer> = {}) => add('text', x, y, w, (extra.line || size * 1.22) * value.split('\n').length + 3, { text: value, size, color: colors.ink, ...extra });
  const card = (y: number, h: number, fill = colors.card, x = 20, w = 353, radius = 18) => add('surface', x, y, w, h, { fill, radius });
  const icon = (name: string, x: number, y: number, size = 23, color = colors.green, action?: string) => add('icon', x, y, size, size, { icon: name, color, action });
  const photo = (asset: string, x: number, y: number, w: number, h = w, radius = 14) => add('photo', x, Math.max(54, y), w, h, { asset, radius });
  const button = (label: string, y: number, action: string, variant: 'primary' | 'secondary' | 'text' = 'primary', extra: Partial<Layer> = {}) => {
    add('button', 20, y, 353, variant === 'text' ? 42 : 54, { text: label, action, size: 16, bold: true, fill: variant === 'primary' ? colors.green : variant === 'secondary' ? colors.card : 'transparent', color: variant === 'primary' ? '#fffdf9' : colors.green, radius: 17, ...extra });
    if (variant === 'primary' && ['sign-in', 'go:food-selector', 'go:nutrition-details', 'go:portion-confirmation', 'market', 'review-reading', 'review-foot', 'go:weekly-plan', 'go:analysis-result', 'review-report', 'create-plan', 'go:catalog-review'].includes(action)) icon('ArrowRight', 332, y + ((extra.h || 54) - 22) / 2, 22, '#fffdf9');
  };
  const heading = (title: string, y = 105, subtitle?: string, size = 36) => { text(title, 24, y, 345, size, { serif: true, bold: true, line: size * 1.1 }); if (subtitle) text(subtitle, 24, y + title.split('\n').length * size * 1.1 + 10, 345, 16, { color: colors.muted, line: 21 }); };
  const header = (title?: string) => { icon('ChevronLeft', 19, 58, 24, colors.ink, 'back'); if (title) text(title, 51, 60, 290, 19, { bold: true, align: 'center' }); };
  const brand = (y = 57, x = 24) => { y = Math.max(54, y); photo('leaf-brand-mark', x, y, 29, 42, 0); text('NutriSole', x + 34, y + 9, 220, 30, { serif: true }); };
  const row = (y: number, label: string, value = '', glyph = 'Info', action?: string, description?: string, extra: Partial<Layer> = {}) => {
    const extraLine = (label.split('\n').length - 1) * 18;
    const rowHeight = (description ? 67 : 49) + extraLine;
    card(y, rowHeight, extra.fill || colors.card, 20, 353, 12);
    icon(glyph, 34, y + (description ? 20 : 13), 21);
    text(label, 68, y + (description ? 10 : 15), value ? 160 : 270, 15, { bold: Boolean(description) });
    if (description) text(description, 68, y + 31 + extraLine, 263, 12, { color: colors.muted, line: 15 });
    if (value) text(value, 218, y + 17, 131, 12, { color: colors.muted, align: 'right' });
    if (action) { icon('ChevronRight', 350, y + 17, 17, colors.muted); add('button', 20, y, 353, rowHeight, { text: label, action, fill: 'transparent', color: 'transparent', radius: 12 }); }
  };
  const field = (label: string, key: string, y: number, placeholder: string, options: Partial<Layer> = {}) => {
    const glyph = label === 'Name' ? 'UserRound' : label === 'Email' ? 'Mail' : options.secure ? 'LockKeyhole' : undefined;
    if (id === 'create-account' || id === 'recover-account') {
      card(y - 5, 87, colors.card, 24, 345, 15); text(label, 80, y + 9, 275, 14, { bold: true });
      add('input', 67, y + 32, 290, 43, { field: key, text: label, placeholder, value: s.fields[key] || '', fill: 'transparent', strokeWidth: 0, radius: 8, size: 14, ...options });
      if (glyph) icon(glyph, 40, y + 31, 22, colors.muted); return;
    }
    if (id === 'sign-in') card(y - 9, 109, colors.card, 20, 353, 18);
    text(label, 26, y, 330, 15, { bold: true });
    add('input', 24, y + 28, 345, options.multiline ? 103 : 55, { field: key, text: label, placeholder, value: s.fields[key] || '', fill: colors.card, radius: 14, size: 16, leadingIcon: id === 'sign-in' ? glyph : undefined, ...options });
    if (id === 'sign-in' && glyph) icon(glyph, 41, y + 46, 21, colors.muted);
  };
  const toggle = (y: number, label: string, key: string, description: string, glyph = 'Info', h = 86) => {
    card(y, h, colors.card, 20, 353, 12); icon(glyph, 34, y + 19, 22);
    text(label, 69, y + 15, 226, 16, { bold: true }); text(description, 69, y + 38, 227, 12, { color: colors.muted, line: 15 });
    add('toggle', 320, y + 24, 43, 26, { text: label, field: key, action: `toggle:${key}`, selected: Boolean(s.toggles[key]) });
  };
  const radio = (y: number, label: string, key: string, value: string, description?: string) => {
    card(y, description ? 66 : 48, colors.card, 24, 345, 10);
    text(label, 76, y + 12, 263, 15, { bold: Boolean(description) }); if (description) text(description, 76, y + 34, 260, 12, { color: colors.muted });
    add('radio', 37, y + 13, 24, 24, { text: label, field: key, selected: s.choices[key] === value });
    add('button', 24, y, 345, description ? 66 : 48, { text: label, action: `choose:${key}:${value}`, fill: 'transparent', color: 'transparent' });
  };
  const note = (value: string, y: number, h = 69, fill = colors.pale, glyph = 'Info') => { card(y, h, fill, 20, 353, 14); icon(glyph, 36, y + 18, 21); text(value, 70, y + 15, 276, 13, { line: 17, color: colors.muted }); };
  const tabs = (y: number, key: string, labels: string[]) => {
    card(y, 43, '#f1efe9', 20, 353, 15);
    labels.forEach((label, i) => add('button', 24 + i * 345 / labels.length, y + 4, 345 / labels.length, 35, { text: label, size: 13, action: `choose:${key}:${label}`, fill: s.choices[key] === label ? colors.green : 'transparent', color: s.choices[key] === label ? '#fff' : colors.muted, radius: 12 }));
  };
  const week = (y: number) => {
    card(y, 69); ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach((d, i) => add('button', 27 + i * 48, y + 9, 46, 50, { text: `${d}\n${[28, 29, 30, 1, 2, 3, 4][i]}`, size: 12, action: `choose:day:${d}`, selected: s.choices.day === d, fill: s.choices.day === d ? colors.green : 'transparent', color: s.choices.day === d ? '#fff' : colors.muted, radius: 14 }));
  };
  const food = s.choices.food || 'Apple'; const info = foodInfo(food);
  switch (id) {
    case 'sign-in':
      brand(95, 103); text('Welcome back.', 20, 198, 353, 44, { serif: true, bold: true, align: 'center', line: 51 });
      text('Your food and health, together.', 20, 260, 353, 19, { align: 'center', color: colors.muted });
      field('Email', 'email', 328, 'Enter your email'); field('Password', 'password', 449, 'Enter your password', { secure: true });
      button('Forgot password?', 548, 'go:recover-account', 'text', { x: 217, w: 156, size: 14 });
      button('Sign in', 607, 'sign-in'); text('or', 20, 683, 353, 13, { align: 'center', color: colors.muted });
      add('surface', 24, 692, 149, 1, { fill: '#ded9cb' }); add('surface', 219, 692, 150, 1, { fill: '#ded9cb' });
      card(713, 80, '#f0f2e9'); text('New to NutriSole?', 39, 733, 278, 17); text('Create account', 39, 757, 278, 17, { bold: true, color: colors.green }); icon('ChevronRight', 342, 745, 23); add('button', 20, 713, 353, 80, { text: 'Create account', action: 'go:create-account', fill: 'transparent', color: 'transparent' }); break;
    case 'create-account':
      brand(62); heading('Create account', 140, 'Join NutriSole to get personalized\nnutrition guidance and build healthier\nhabits, one meal at a time.', 38);
      field('Name', 'name', 295, 'Your full name'); field('Email', 'email', 391, 'you@example.com'); field('Password', 'password', 487, 'Create a password', { secure: true });
      text('Use at least 8 characters.', 26, 582, 320, 12, { color: colors.muted });
      add('toggle', 27, 625, 27, 26, { text: 'Agree to Terms and Privacy Policy', field: 'terms', action: 'toggle:terms', selected: Boolean(s.toggles.terms) });
      text('I agree to the Terms and Privacy Policy', 65, 630, 303, 13); add('button', 89, 652, 265, 24, { text: 'Read Terms and Privacy Policy', action: 'terms', fill: 'transparent', color: 'transparent' });
      button('Create account', 679, 'create-account'); button('Already registered? Sign in', 765, 'go:sign-in', 'text', { size: 14 }); break;
    case 'verify-email':
      header(); brand(53, 67); card(146, 142, colors.pale, 126, 142, 71); icon('MailCheck', 160, 184, 74);
      heading('Check your inbox.', 316, undefined, 36); text('We sent a verification link to\nyour email.', 24, 373, 345, 19, { align: 'center', color: colors.muted, line: 25 });
      note('Open the link to activate\nyour account.', 448, 88); button('Open email app', 552, 'verify-demo');
      text('Or', 20, 631, 353, 13, { align: 'center', color: colors.muted }); row(665, 'Resend link', '', 'RefreshCw', 'resend'); row(735, 'Use another email', '', 'UserRound', 'go:create-account'); break;
    case 'recover-account':
      header(); brand(112); heading('Reset your\npassword', 190, 'Enter your email and we will send a\nrecovery link if an account exists.', 47);
      field('Email', 'email', 398, 'you@example.com'); button('Send recovery link', 476, 'recover'); button('Back to sign in', 552, 'go:sign-in', 'text', { size: 14 }); break;
    case 'reset-password':
      header('Choose a new password'); field('New password', 'newPassword', 129, 'Enter new password', { secure: true }); text('At least 8 characters', 26, 225, 345, 13, { color: colors.muted });
      field('Confirm password', 'confirmPassword', 275, 'Confirm new password', { secure: true }); button('Save new password', 398, 'reset-password'); break;
    case 'analysis-result':
      header(); brand(46, 53); heading('Food assessment', 109, 'Review what we can see in your photo.', 35);
      card(181, 110); photo('apple-thumbnail', 29, 192, 111, 98); text('Apple', 155, 209, 180, 21, { bold: true }); text('Sample analysis', 155, 243, 180, 14, { color: colors.muted });
      card(307, 104, colors.pale); icon('Leaf', 43, 339, 36); text('VISIBLE GRADE', 117, 322, 222, 10, { color: colors.muted }); text('A', 117, 339, 80, 39, { serif: true, color: colors.green }); text('Good visible condition', 117, 383, 232, 14, { color: colors.green });
      row(425, 'Ripeness', 'Even colour', 'Apple', 'evidence'); row(472, 'Surface', 'Minor marks', 'Flower', 'evidence'); row(519, 'Evidence', 'Visible features only', 'Search', 'evidence');
      text('Model v1.0 · Rubric v1.0\nA photo cannot confirm food safety.', 27, 577, 345, 11, { color: colors.muted, line: 16 });
      row(626, 'Market reference', '', 'ShoppingCart', 'go:market-reference', 'Typical seasonal info'); row(700, 'Nutrition', '', 'ChartNoAxesColumnIncreasing', 'go:nutrition-details', 'Typical values for 1 medium (sample)');
      button('Confirm food', 778, 'go:food-selector'); break;
    case 'market-reference':
      header('Market reference'); card(109, 117); photo('apple-thumbnail', 30, 120, 95); text('Apple', 140, 143, 196, 31, { serif: true }); text('Grade A', 140, 185, 190, 14, { color: colors.muted });
      row(236, 'Market', s.choices.market || '', 'MapPin', 'market', 'Select a market'); row(302, 'Unit', 'per kg', 'Weight', 'unit-market');
      card(382, 215, colors.pale); icon('ChartNoAxesColumnIncreasing', 167, 409, 47); text('No verified price yet', 30, 492, 333, 24, { serif: true, align: 'center' }); text('Choose a market to check dated,\ncomparable observations.', 31, 534, 332, 15, { color: colors.muted, align: 'center', line: 21 });
      row(611, 'Source', '—', 'NotebookText', undefined, 'Not available'); row(682, 'Observed', '—', 'CalendarDays', undefined, 'Not available'); button('Choose market', 769, 'market'); break;
    case 'capture-retry':
      header('Try another photo'); photo('extension-blurred-apple', 22, 113, 349, 247, 18); heading('The image is too blurred', 389, undefined, 28);
      text('Frame one item in good light.', 24, 437, 345, 16, { color: colors.muted, align: 'center' });
      note('Keep the item in focus\nHold your camera steady and\nmake sure the item is sharp.', 476, 97, colors.pale, 'Scan'); note('Avoid multiple items\nFrame one supported produce\nitem at a time.', 581, 97, colors.pale, 'Apple');
      button('Retake photo', 696, 'go:scan'); button('Choose a photo', 759, 'choose-photo', 'secondary'); break;
    case 'food-selector':
      header(); text('Choose the food', 58, 60, 310, 31, { serif: true, bold: true }); add('input', 24, 111, 345, 51, { field: 'foodSearch', text: 'Search supported foods', placeholder: 'Search supported foods', value: s.fields.foodSearch || '', fill: '#f8f6f0', radius: 16, size: 14 });
      text('SUPPORTED PRODUCE', 25, 190, 330, 11, { color: colors.muted });
      if (!Object.keys(foods).some(name => name.toLowerCase().includes((s.fields.foodSearch || '').toLowerCase()))) text('No supported foods match your search.', 25, 242, 343, 16, { color: colors.muted });
      Object.keys(foods).filter(name => name.toLowerCase().includes((s.fields.foodSearch || '').toLowerCase())).forEach((name, i) => {
        const y = 221 + i * 113; add('surface', 24, y, 345, 104, { fill: food === name ? '#f0f6ed' : colors.card, radius: 15, stroke: food === name ? colors.green : colors.border, strokeWidth: food === name ? .8 : .6 }); photo(foodInfo(name).asset, 36, y + 10, 83, 83, 12); text(name, 136, y + 27, 180, 18, { bold: true }); text('Raw · Supported food', 136, y + 59, 178, 13, { color: colors.muted });
        add('radio', 326, y + 37, 27, 27, { text: name, selected: food === name, field: 'food', action: `choose:food:${name}` }); add('button', 24, y, 292, 104, { text: `Select ${name}`, action: `choose:food:${name}`, fill: 'transparent', color: 'transparent' });
      });
      note('Your choice is kept separate from the original\nprediction.', 694, 57, colors.card); button(`Confirm ${food}`, 771, 'go:nutrition-details'); break;
    case 'nutrition-details': {
      header('Nutrition'); card(102, 149); photo(info.asset, 34, 115, 113); text(`${food} · Raw`, 163, 153, 193, 23, { bold: true }); text('Sample catalog', 163, 190, 183, 14, { color: colors.muted });
      row(269, 'Basis', s.choices.basis, 'Scale', 'basis'); const multiplier = s.choices.basis === 'per medium' ? info.grams / 100 : 1;
      [['Energy', `${Math.round(info.calories * multiplier)} kcal`, 'Zap'], ['Carbohydrate', `${(Number(info.carbs) * multiplier).toFixed(1)} g`, 'Leaf'], ['Protein', `${(Number(info.protein) * multiplier).toFixed(1)} g`, 'Activity'], ['Fat', `${(Number(info.fat) * multiplier).toFixed(1)} g`, 'Droplet'], ['Fibre', `${(Number(info.fibre) * multiplier).toFixed(1)} g`, 'Leaf']].forEach(([label, value, glyph], i) => row(337 + i * 63, label, value, glyph));
      row(664, 'Source', '', 'NotebookText', 'catalog-source', 'Demo catalog v1 · Sample values only'); button('Confirm portion', 751, 'go:portion-confirmation'); break;
    }
    case 'glucose-overview':
      header(); heading('Glucose history', 88, 'Sep 28 – Oct 4', 38); week(171);
      card(260, 235); icon('Droplet', 167, 308, 49);
      if (s.readings.length) { text(`${s.readings.length} manual reading${s.readings.length > 1 ? 's' : ''}`, 26, 386, 341, 25, { serif: true, align: 'center' }); button('View latest reading', 436, 'latest-reading', 'text'); }
      else { text('No readings yet', 25, 386, 343, 26, { serif: true, align: 'center' }); text('Add a meter reading to start your history.', 25, 426, 343, 13, { align: 'center', color: colors.muted }); }
      row(513, 'Unit', s.choices.unit, 'Droplet', 'reading-unit', 'Display format for your readings'); row(584, 'Source', 'Manual', 'Flower', 'manual-source', 'How you add your readings'); row(655, 'Health connections', '', 'Heart', 'go:health-connections', 'Sync from your device or apps');
      button('Add reading', 740, 'new-reading', 'primary', { h: 48 }); button('Connect a health source', 798, 'go:health-connections', 'secondary', { h: 37, size: 14 }); break;
    case 'add-reading':
      header('Add reading'); card(109, 192); text('Reading', 34, 131, 320, 20, { bold: true });
      add('input', 33, 170, 326, 60, { field: 'reading', text: 'Reading', placeholder: 'Enter value', numeric: true, value: s.fields.reading || '', radius: 14, size: 20, fill: colors.card });
      tabs(246, 'unit', ['mg/dL', 'mmol/L']); row(315, 'Measured on', '', 'CalendarDays', 'reading-date', s.choices.date); row(389, 'Time', '', 'Clock3', 'reading-time', s.choices.time); row(463, 'Context', '', 'Utensils', 'reading-context', s.choices.context); row(537, 'Source', '', 'NotebookText', undefined, 'Manual meter entry');
      text('Pacific Time', 26, 612, 331, 12, { color: colors.muted }); note('Enter an existing meter reading.\nNutriSole does not measure glucose.', 643, 64, colors.card); button('Review reading', 757, 'review-reading'); break;
    case 'reading-detail': {
      header('Reading details'); const r = s.currentReading || { value: 110, unit: 'mg/dL', date: 'Sep 30, 2026', time: '8:15 AM', context: 'Before a meal', source: 'Manual entry' };
      card(106, 188); text(s.currentReading ? 'Manual record' : 'Sample record', 38, 125, 300, 12, { color: colors.green }); text(s.readingRemoved ? 'Removed' : `${r.value}`, 36, 155, 181, s.readingRemoved ? 39 : String(r.value).length > 3 ? 64 : 81, { serif: true, line: 85 }); text(s.readingRemoved ? '' : r.unit, 218, 219, 126, 24, { color: colors.muted }); text(s.currentReading ? 'Entered in this frontend session' : 'Demo fixture', 37, 264, 305, 13, { color: colors.muted });
      row(312, 'Date', '', 'CalendarDays', undefined, r.date); row(383, 'Time', '', 'Clock3', undefined, r.time); row(454, 'Context', '', 'Utensils', undefined, r.context); row(525, 'Source', '', 'NotebookText', undefined, r.source); row(596, 'Time zone', '', 'Globe', undefined, 'Pacific Time');
      button('Edit reading', 690, 'edit-reading', 'primary', { disabled: s.readingRemoved }); button('Remove record', 759, 'remove-reading', 'text', { size: 14, disabled: s.readingRemoved }); break;
    }
    case 'health-connections':
      header('Health connections'); heading('Choose what you share.', 110, 'Connect your health data to get a more\ncomplete picture and more personalized\nnutrition insights.', 29);
      row(244, 'Apple Health', 'Not connected', 'Heart', 'provider-info', 'Export your health data\nto NutriSole'); text('CHOOSE DATA TO SHARE', 28, 348, 330, 11, { color: colors.muted });
      toggle(370, 'Glucose readings', 'shareGlucose', 'Share your glucose records', 'Droplet', 69); toggle(442, 'Activity records', 'shareActivity', 'Share workouts and daily activity', 'PersonStanding', 69);
      row(522, 'Last sync', 'Not synced', 'Clock3'); row(570, 'Imported records', 'None', 'NotebookText'); button('Review permissions', 654, 'permissions'); note('Manual entry is always available.', 730, 58, colors.card); break;
    case 'plan-generation':
      header(); brand(92); heading('Build your\nweekly plan', 144, 'Create a personalized meal plan based\non your preferences and recent activity.', 40);
      row(302, 'Diet', 'Balanced, higher protein', 'Apple', 'profile-diet'); row(350, 'Allergens', 'Tree nuts, shellfish', 'Flower', 'profile-allergens'); row(398, 'Activity', 'Strength training', 'PersonStanding', 'profile-activity'); row(446, 'Mobility', 'None reported', 'Accessibility', 'go:foot-questionnaire');
      note('Limited personalization\nNo glucose readings selected. This plan\nuses your preferences.', 506, 82);
      text('Plan week', 27, 608, 340, 16, { bold: true }); row(636, 'Sep 28 – Oct 4', '', 'CalendarDays', 'plan-week', 'Mon, Sep 28 – Sun, Oct 4, 2026'); text('Data used', 27, 713, 330, 16, { bold: true }); row(738, 'Last 7 days', '', 'CalendarDays', 'plan-window', 'Meals, activity, and preferences'); button('Create plan', 804, 'create-plan', 'primary', { h: 40 }); break;
    case 'activity-plan':
      brand(54); photo('alex-avatar', 333, 54, 39, 39, 22); icon('ChevronLeft', 20, 134, 23, colors.ink, 'back'); text('Weekly Activity', 61, 127, 305, 31, { serif: true }); text('Sep 28 – Oct 4', 62, 172, 286, 15, { color: colors.muted }); week(201); text('Today', 169, 280, 62, 12, { align: 'center', color: colors.green });
      { const deferred = s.choices.comfort === 'Concern' || s.choices.mobility === 'Limited';
      card(310, 378); icon('PersonStanding', 42, 347, 44); text('WEDNESDAY', 134, 337, 217, 11, { color: colors.muted }); text(deferred ? 'Activity deferred' : s.choices.activity || 'Gentle movement', 134, 359, 222, 26, { serif: true }); text(deferred ? 'Recorded concern needs review' : 'Sample suggestion · 15 min', 134, 399, 224, 14, { color: colors.muted });
      icon('Clock3', 39, 443, 18); text(deferred ? 'No activity scheduled' : 'Any comfortable time', 70, 444, 270, 14); text('BASED ON YOUR RECORDED PREFERENCES', 36, 493, 315, 10, { color: colors.muted }); text(deferred ? 'Seek a qualified assessment for the\nrecorded concern. Movement suggestions\nare deferred until it is reviewed.' : 'A short, low-intensity walk can support\nyour overall wellbeing and fit easily\ninto your day.', 37, 517, 319, 16, { line: 21, color: colors.muted });
      button(deferred ? 'Review foot support' : s.activityComplete ? 'Completed' : 'Mark complete', 601, deferred ? 'go:foot-guidance' : 'complete-activity', 'primary', { x: 34, w: 325, h: 48 }); button('Substitute', 658, 'substitute-activity', 'secondary', { x: 34, w: 325, h: 46, disabled: deferred }); note('If a recorded concern needs assessment,\nactivity is deferred.', 755, 65, colors.card); } break;
    case 'plan-rationale':
      header('Why this plan?'); text(`Sep 28 – Oct 4 · Version ${s.planVersion}`, 27, 100, 340, 12, { color: colors.muted }); heading('Built around your\npreferences.', 131, 'Your weekly plan is tailored to the information\nyou have shared, so it fits your goals and lifestyle.', 38);
      row(300, 'Dietary choices', '', 'Apple', 'profile-diet', 'Meals match your preferences\nfor a balanced, higher protein diet.'); row(388, 'Declared allergens excluded', '', 'Flower', 'profile-allergens', 'Tree nuts and shellfish are\nleft out of your plan.'); row(476, 'Recorded mobility constraints\nrespected', '', 'PersonStanding', 'go:foot-questionnaire', s.choices.mobility === 'Limited' || s.choices.comfort === 'Concern' ? 'A concern is recorded. Activity is\ndeferred pending qualified assessment.' : 'None reported. Activity follows your\nrecorded preferences.');
      text(`Profile v${s.planVersion}`, 35, 581, 319, 17, { bold: true }); text('Data window: last 7 days', 35, 609, 319, 12, { color: colors.muted }); row(636, 'Glucose readings', 'None', 'Droplet'); row(682, 'Dietary preferences', 'Set', 'UserRound'); row(728, 'Rule set', 'v1', 'NotebookText'); button('Review weekly plan', 784, 'go:weekly-plan', 'primary', { h: 42 }); break;
    case 'foot-questionnaire':
      header('Foot support'); text('Step 1 of 2', 25, 87, 343, 12, { align: 'center', color: colors.muted }); heading('Comfort starts here.', 116, 'A few questions about fit and movement.', 33);
      text('Shoe fit', 36, 211, 319, 16, { bold: true }); text('How do your shoes usually feel?', 36, 239, 319, 12, { color: colors.muted }); ['Comfortable', 'Tight', 'Loose'].forEach((v, i) => radio(264 + i * 51, v, 'fit', v));
      text('Current comfort', 36, 443, 319, 16, { bold: true }); text('How would you describe your foot comfort\nduring daily activities?', 36, 471, 319, 12, { line: 15, color: colors.muted }); ['No concern', 'Concern'].forEach((v, i) => radio(514 + i * 51, v, 'comfort', v));
      text('Mobility', 36, 636, 319, 16, { bold: true }); text('How would you describe your current mobility?', 36, 662, 319, 12, { color: colors.muted }); ['Unrestricted', 'Limited'].forEach((v, i) => radio(687 + i * 48, v, 'mobility', v)); button('Review answers', 788, 'review-foot', 'primary', { h: 44 }); break;
    case 'foot-guidance':
      header('Foot support'); text('SAMPLE RESPONSE', 26, 98, 341, 10, { color: colors.muted }); heading('Everyday fit and\ncomfort', 121, 'Here are some general tips based on\nyour answers. These are not a diagnosis\nand not a substitute for professional advice.', 37);
      card(280, 304, colors.pale); icon('Footprints', 39, 309, 37); text('Everyday fit and comfort', 95, 307, 256, 18, { bold: true }); text('Support your feet with simple\npractical steps.', 95, 339, 258, 14, { color: colors.muted, line: 18 });
      row(392, 'Choose a comfortable fit', '', 'Footprints', 'fit-tip', 'Look for enough room, a secure\nfit, and stable support.'); row(478, 'Review changes in comfort', '', 'Footprints', 'comfort-tip', 'Notice any patterns and adjust\nyour footwear or routine.'); text('Based on your questionnaire · Rule set v1', 37, 561, 320, 10, { color: colors.muted });
      note(s.choices.comfort === 'Concern' || s.choices.mobility === 'Limited' ? 'Concern recorded\nSeek a qualified assessment. Activity is deferred.' : 'Concern reported?\nSeek a qualified assessment\nwhen needed.', 613, 83, colors.card);
      button('Review my answers', 713, 'go:foot-questionnaire', 'primary', { h: 49 }); toggle(785, 'Save this session', 'retainFoot', 'Keep a copy in your profile.', 'NotebookText', 59); break;
    case 'assistant':
      header(); photo('leaf-brand-mark', 46, 55, 26, 38, 0); text('NutriSole Assistant', 78, 63, 292, 27, { serif: true }); row(119, s.toggles.healthContext ? 'Health context enabled · Demo' : 'General questions · No health context', '', 'MessageSquare');
      card(183, 57, colors.pale, 167, 164, 17); text('What can I ask you?', 181, 203, 145, 15); photo('alex-avatar', 339, 193, 36, 36, 18);
      card(249, 150, colors.card, 62, 294, 18); photo('leaf-brand-mark', 22, 258, 27, 38, 0);
      text(s.fields.assistantResponse || 'I can help with food, everyday\nactivity and using NutriSole.\n\nYou can ask for meal ideas,\nnutrition tips, help with your plan,\nor how to make healthier choices.', 78, 266, 260, 15, { line: 20 });
      add('button', 71, 407, 116, 34, { text: 'View sources', size: 12, action: 'assistant-sources', fill: 'transparent', color: colors.muted }); add('button', 200, 407, 156, 34, { text: 'Report a concern', size: 12, action: 'go:report-output', fill: 'transparent', color: colors.muted });
      note('I do not diagnose or advise on\nmedicines or insulin doses.', 451, 64, '#f2efe5'); text('Try asking about', 26, 538, 341, 13, { color: colors.muted });
      add('button', 24, 568, 163, 54, { text: 'Food questions', action: 'assistant-food', size: 14, fill: colors.card, color: colors.green, radius: 14 }); add('button', 197, 568, 173, 54, { text: 'Using my plan', action: 'assistant-plan', size: 14, fill: colors.card, color: colors.green, radius: 14 });
      add('input', 22, 775, 290, 62, { text: 'Ask a question', field: 'assistantQuestion', placeholder: 'Ask a question…', value: s.fields.assistantQuestion || '', size: 15, radius: 19, fill: colors.card }); add('button', 322, 786, 45, 45, { text: 'Send question', icon: 'Send', action: 'assistant-send', fill: colors.green, color: '#fff', radius: 24 }); break;
    case 'privacy-data-rights':
      header('Privacy & Consent'); heading('Your data,\nyour choice.', 110, 'Control how your information is used\nand manage your data at any time.', 43);
      toggle(282, 'Health import', 'healthImport', 'Allow importing data from\nApple Health to personalize\nyour experience.', 'Heart', 105); toggle(391, 'Retain food photos', 'retainPhotos', 'Save your food photos to\nimprove your experience\nand show your history.', 'Camera', 105); toggle(500, 'Use health context in Assistant', 'healthContext', 'Allow your meal and health data\nto be used for more personalized\nguidance.', 'Sparkles', 112);
      row(625, 'Export my data', '', 'Download', 'export', s.exportStatus); row(694, 'Manage retained records', '', 'NotebookText', 'retained'); row(748, 'Delete account', '', 'Trash2', 'delete-account', 'Deletion requires sign-in confirmation.'); button('Save preferences', 815, 'save-preferences', 'primary', { h: 33, size: 14 }); break;
    case 'reminders':
      header(); heading('Reminders', 99, 'Stay on track with gentle reminders\nthat fit your routine.', 37);
      toggle(193, 'Meal reminders', 'mealReminder', 'Gentle reminders to log your meals', 'Utensils', 75); toggle(269, 'Glucose logging', 'glucoseReminder', 'Remind me to log my glucose', 'Droplet', 75); toggle(345, 'Plan check-in', 'planReminder', 'Weekly check-in to review progress', 'CalendarDays', 75);
      row(445, 'Quiet hours', '', 'Moon', 'quiet-hours', s.fields.quietHours || '10:00 PM – 7:00 AM'); row(518, 'Time zone', '', 'Clock3', 'reminder-zone', s.fields.reminderZone || 'Pacific Time'); note('Notification previews hide health details.', 613, 56); row(684, 'Notifications', '', 'Bell', 'notification-permission', 'Not enabled'); button('Save preferences', 778, 'save-reminders'); break;
    case 'report-output':
      header('Report a result'); card(100, 78); photo('apple-thumbnail', 32, 108, 59); text('Apple assessment', 105, 117, 244, 16, { bold: true }); text('Sample output', 105, 145, 244, 13, { color: colors.muted });
      heading('What needs review?', 210, 'Help us understand what is not right.', 24); [['Wrong food', 'The food was identified incorrectly'], ['Misleading price', 'The price or its source seems wrong'], ['Unsuitable guidance', 'The advice is not appropriate or safe'], ['Other', 'Something else']].forEach(([v, d], i) => radio(266 + i * 66, v, 'reason', v, d));
      text('Tell us more (optional)', 26, 550, 341, 18, { bold: true }); text('Add any details that could help us improve.', 26, 579, 341, 12, { color: colors.muted }); add('input', 25, 611, 343, 105, { field: 'reportDetails', text: 'Report details', value: s.fields.reportDetails || '', placeholder: 'Share a few details (optional)', multiline: true, maxLength: 500, size: 14, fill: colors.card, radius: 14 });
      note('Only this output reference, your reason and\noptional details will be shared.', 734, 64, colors.pale, 'LockKeyhole'); button('Review report', 811, 'review-report', 'primary', { h: 35, size: 14 }); break;
    case 'report-status':
      header('My report'); card(103, 220, colors.pale); icon('FileClock', 164, 133, 54); text(s.reportResolved ? 'Resolved' : 'In review', 24, 228, 345, 38, { serif: true, align: 'center' }); text(s.reportSubmitted ? 'Your demo report is saved for review.' : 'Your report has been received for review.', 26, 286, 341, 14, { color: colors.muted, align: 'center' });
      row(344, 'Sample ID', 'DEMO-104'); row(391, 'Reason', s.choices.reason || 'Wrong food'); row(438, 'Created', 'Sep 30, 2026', 'CalendarDays'); row(485, 'Shared context', 'Output reference only', 'UserRound');
      ['Received', 'In review', 'Resolved'].forEach((v, i) => { icon(i === 0 || (i === 2 && s.reportResolved) ? 'Check' : 'Clock3', 39, 573 + i * 83, 22); text(v, 82, 572 + i * 83, 273, 15, { bold: true, color: i === 2 && !s.reportResolved ? colors.muted : colors.ink }); text(['Sep 30, 2026\nYour report has been submitted.', 'We are reviewing your report.', 'You will see the outcome here.'][i], 82, 600 + i * 83, 271, 12, { color: colors.muted, line: 17 }); }); button('View reported result', 803, 'go:analysis-result', 'primary', { h: 41 }); break;
    case 'personal-history':
      header(); brand(52, 54); heading('Your history', 110, 'Sample records: food, meals, and plans\nin one place.', 37); tabs(215, 'history', ['All', 'Food', 'Meals', 'Plans']); row(275, 'Last 7 days', '', 'CalendarDays', 'history-window', 'Thu, Sep 24 – Wed, Sep 30, 2026');
      { const items = [...s.meals.map(m => [m.draft ? 'Food' : 'Meals', m.draft ? 'Saved draft · This session' : 'Meal · This session', m.food, `${Math.round(m.grams)} g · ≈ ${m.calories} cal${m.draft ? ' · Not consumed' : ''}`, foodInfo(m.food).asset, 'portion-confirmation']), ['Food', 'Food assessment', 'Apple', 'Sep 30, 2026 · Good match', 'apple-thumbnail', 'analysis-result'], ['Meals', 'Meal', 'Apple', 'Sep 30, 2026 · 182 g', 'apple-thumbnail', 'portion-confirmation'], ['Plans', 'Weekly plan', 'Weekly Plan', 'Sep 28 – Oct 4, 2026 · v1', 'chicken-quinoa-bowl', 'plan-rationale'], ['Food', 'Saved draft', 'Apple', 'Saved for later', 'apple-thumbnail', 'portion-confirmation']];
        items.filter(i => s.choices.history === 'All' || i[0] === s.choices.history).forEach((i, n) => { const y = 354 + n * 101; card(y, 94); photo(i[4], 31, y + 10, 74); text(i[1], 119, y + 10, 227, 11, { color: colors.green }); text(i[2], 119, y + 33, 223, 18, { bold: true }); text(i[3], 119, y + 62, 224, 12, { color: colors.muted }); add('button', 20, y, 353, 94, { text: `Open ${i[1]}`, action: `go:${i[5]}`, color: 'transparent', fill: 'transparent' }); }); }
      scene.height = Math.max(852, 850 + s.meals.length * 101); button('Filter records', 777 + s.meals.length * 101, 'history-filter'); break;
    case 'catalog-queue':
      brand(47); text('Catalog curator', 71, 102, 274, 14, { color: colors.muted }); heading('Catalog review', 149, 'Review and edit shared food catalog entries\nbefore they are published.', 36); tabs(251, 'catalog', ['Pending', 'Published', 'Withdrawn']);
      if (s.choices.catalog === 'Pending') ['Apple nutrition mapping', 'Apple market observation'].forEach((v, i) => { const y = 309 + i * 200; card(y, 182); photo('apple-thumbnail', 32, y + 14, 88); text('Unpublished', 135, y + 17, 215, 12, { color: '#9a7925' }); text(v, 135, y + 45, 217, 16, { bold: true }); text(i ? 'Observation date required' : 'Unit and source review', 135, y + 75, 217, 13, { color: colors.muted }); text(`Record type\n${i ? 'Market observation' : 'Apple'}`, 35, y + 126, 173, 12, { line: 18, color: colors.muted }); text(`Submitted\nSep ${i ? 30 : 29}, 2026`, 229, y + 126, 124, 12, { line: 18, color: colors.muted }); add('button', 20, y, 353, 182, { text: `Review ${v}`, action: 'go:catalog-review', fill: 'transparent', color: 'transparent' }); });
      else note(`No ${s.choices.catalog.toLowerCase()} sample entries.`, 320, 80, colors.card);
      button('Review next entry', 735, 'go:catalog-review'); break;
    case 'catalog-review':
      header(); brand(48, 61); heading('Review catalog entry', 112, 'Check the details before publishing.', 32); card(193, 132); photo('apple-thumbnail', 33, 210, 112); text('Apple', 166, 239, 186, 24, { bold: true }); text('Sample draft', 166, 275, 185, 14, { color: colors.muted });
      row(347, 'Food form', 'Raw', 'Leaf', 'catalog-form'); row(394, 'Source', s.fields.catalogSource || 'Not verified', 'Link', 'catalog-source-edit'); row(441, 'Unit', 'per kg', 'Weight', 'unit-market'); row(488, 'Observation date', s.fields.observationDate || 'Not supplied', 'CalendarDays', 'catalog-date'); row(535, 'Grade applicability', 'Pending', 'Award', 'catalog-grade'); note('Publishing is blocked\nuntil the source and date are verified.', 591, 70, '#fbf3df', 'TriangleAlert');
      button('Save review', 677, 'catalog-save', 'primary', { h: 49 }); button('Reject entry', 735, 'catalog-reject', 'secondary', { h: 46 }); button('Publish', 791, 'catalog-publish', 'primary', { h: 46, disabled: true, fill: '#d6d6d3', color: '#838780' }); break;
    case 'model-release':
      brand(40); photo('alex-avatar', 331, 46, 39, 39, 22); text('MODEL ADMINISTRATOR', 26, 104, 341, 10, { color: colors.muted }); heading('Release review', 128, 'Review the model package, confirm required\nelements, and activate when ready.', 35);
      card(230, 95); text('CANDIDATE', 35, 246, 318, 10, { color: colors.muted }); text('Produce model v1.1 · Draft', 35, 268, 226, 17, { bold: true }); text('Created Sep 30, 2026', 35, 297, 217, 12, { color: colors.muted }); text('Not ready\nfor activation', 281, 264, 76, 11, { color: colors.green, align: 'center', line: 16 });
      text('Release checklist', 27, 347, 339, 17, { bold: true }); text('All items must be complete to activate.', 27, 378, 340, 12, { color: colors.muted });
      [['Model manifest', 'Present', 'Model details and files', 'NotebookText'], ['Dataset licence', 'Review needed', 'Data source and usage rights', 'Database'], ['Class thresholds', 'Review needed', 'Category configuration', 'Settings'], ['Safety regression', 'Pending', 'Automated test results', 'Shield']].forEach(([v, val, d, g], i) => row(408 + i * 62, v, val, g, 'release-evidence', d));
      text('Active package', 27, 671, 339, 15, { bold: true }); row(694, 'v1.0 · Demo', 'Active', 'Package', undefined, 'Activated Sep 15, 2026'); button('Review evidence', 758, 'release-evidence', 'primary', { h: 38, size: 14 }); button('Activate package', 802, 'activate-package', 'primary', { h: 37, size: 14, disabled: true, fill: '#d6d6d3', color: '#838780' }); scene.height = 930; row(858, 'Rollback history', '', 'RefreshCw', 'rollback'); break;
    case 'operations-audit':
      brand(42); text('OPERATIONS ADMINISTRATOR', 27, 102, 339, 10, { color: colors.muted }); heading('Audit review', 131, 'Review recent system events and\nactions for security and compliance.', 36);
      row(236, 'Date', '', 'CalendarDays', 'audit-date', s.fields.auditDate || 'Sep 30, 2026'); row(313, 'Event category', '', 'Filter', 'audit-category', s.choices.auditCategory || 'All events'); button('Filter events', 400, 'filter-audit'); text('Sample audit events', 28, 485, 233, 17, { bold: true }); text('Redacted metadata only', 259, 490, 111, 10, { color: colors.muted });
      [['Catalog review saved', 'Success', 'REQ-104 · 9:10 AM', 'NotebookText'], ['Model activation', 'Denied', 'REQ-103 · 9:04 AM', 'Settings'], ['Protected access', 'Denied', 'REQ-102 · 8:55 AM', 'Shield']].filter(i => !s.choices.auditCategory || s.choices.auditCategory === 'All events' || s.choices.auditCategory === i[1]).forEach(([v, val, d, g], i) => row(525 + i * 97, v, val, g, `audit-detail:${v}`, d)); break;
    case 'report-triage':
      brand(45); text('STAFF', 27, 109, 339, 11, { color: colors.muted }); heading('Review report', 134, 'Check the details and add your review.', 36);
      card(218, 252); text('DEMO-104', 34, 233, 309, 21, { bold: true }); text('Food analysis report', 34, 264, 314, 13, { color: colors.muted }); row(292, 'Reason', 'Wrong food', 'NotebookText'); row(335, 'Output reference', 'ANALYSIS-DEMO-17', 'ChartNoAxesColumnIncreasing'); row(378, 'Created', 'Wed, Sep 30, 2026', 'CalendarDays'); row(421, 'Shared context', 'Redacted', 'LockKeyhole');
      text('Review note', 29, 499, 335, 16, { bold: true }); add('input', 25, 531, 343, 91, { field: 'triageNote', text: 'Review note', value: s.fields.triageNote || '', placeholder: 'Add your review note (optional)…', multiline: true, maxLength: 500, size: 14, fill: colors.card, radius: 14 }); text('Status', 29, 657, 335, 16, { bold: true }); tabs(686, 'triage', ['In review', 'Resolved']); button('Save review', 761, 'triage-save'); note('Original analysis evidence is retained.', 821, 31, colors.card); break;
    case 'portion-confirmation': {
      header('Confirm portion'); card(113, 125); photo(info.asset, 33, 126, 93); text(food, 145, 149, 210, 24, { bold: true }); text('Raw · Demo catalog v1', 145, 188, 210, 14, { color: colors.muted }); heading('How much will you eat?', 277, 'Adjust the portion before logging.', 28); tabs(367, 'portion', ['By amount', 'By weight', 'By size']);
      if (s.choices.portion === 'By weight') field('Edible weight in grams', 'grams', 441, String(info.grams), { numeric: true });
      else if (s.choices.portion === 'By size') { row(445, 'Size', s.choices.size, 'Apple', 'portion-size'); field('Amount', 'amount', 511, '1', { numeric: true }); }
      else { add('button', 32, 459, 53, 53, { text: 'Decrease amount', icon: 'Minus', action: 'amount-minus', fill: colors.card, color: colors.ink, radius: 27 }); text(s.fields.amount || '1', 100, 464, 70, 35, { align: 'center', bold: true }); add('button', 187, 459, 53, 53, { text: 'Increase amount', icon: 'Plus', action: 'amount-plus', fill: colors.card, color: colors.ink, radius: 27 }); text(`medium ${food.toLowerCase()}`, 255, 468, 114, 17, { bold: true }); }
      const grams = s.choices.portion === 'By weight' ? Number(s.fields.grams || info.grams) : Number(s.fields.amount || 1) * info.grams * (s.choices.portion === 'By size' ? { small: .75, medium: 1, large: 1.25 }[s.choices.size as 'small' | 'medium' | 'large'] || 1 : 1);
      note(Number.isFinite(grams) && grams > 0 ? `≈ ${Math.round(info.calories * grams / 100)} calories\nEstimated for ${Math.round(grams)} g edible portion.\nValues are estimates.` : 'Check your portion\nEnter a positive edible amount or weight.\nNo meal will be logged until it is valid.', 632, 88, colors.pale, 'Apple'); button('Log meal', 743, 'save-meal'); button('Save for later', 802, 'draft-meal', 'text'); break;
    }
    case 'flow-directory':
      brand(58); heading('Explore NutriSole', 132, 'Choose a frontend demo flow.', 36);
      [['Accounts', 'sign-in', 'UserRound'], ['Food assessment', 'analysis-result', 'Apple'], ['Glucose & connections', 'glucose-overview', 'Droplet'], ['Build a plan', 'plan-generation', 'CalendarDays'], ['Foot support', 'foot-questionnaire', 'Footprints'], ['Assistant', 'assistant', 'MessageSquare'], ['Privacy & reminders', 'privacy-data-rights', 'LockKeyhole'], ['Reports & history', 'personal-history', 'NotebookText'], ['Staff workspace', 'staff-workspace', 'Settings']].forEach(([v, target, g], i) => row(224 + i * 62, v, '', g, target === 'staff-workspace' ? target : `go:${target}`));
      button('Return home', 798, 'go:home', 'text'); break;
  }
  // Source concepts omit OS chrome. Reserve the protected 34 px home-indicator
  // region without changing the six reference screens or their shared canvas.
  layers.forEach(l => { if (l.y >= 100) { l.y = 100 + (l.y - 100) * .95; if (l.kind !== 'text') l.h *= .95; } });
  scene.height = 100 + (scene.height - 100) * .95 + 34;
  return scene;
}
