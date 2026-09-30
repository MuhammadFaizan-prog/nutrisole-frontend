import { useState, type CSSProperties, type FocusEvent } from 'react';
import { KeyboardInput, KeyboardTextarea, useKeyboard } from '../../mobile';
import { View, Pressable } from '../primitives';
import Icons from './Icons';
export type InputProps = { label: string; value: string; placeholder?: string; secure?: boolean; numeric?: boolean; multiline?: boolean; maxLength?: number; onChange: (value: string) => void; style: Record<string, unknown> };
export default function Input({ label, value, placeholder, secure, numeric, multiline, maxLength = 100, onChange, style }: InputProps) {
  const keyboard = useKeyboard();
  const [visible, setVisible] = useState(false);
  const blur = (e: FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => { if (!(e.relatedTarget instanceof HTMLInputElement || e.relatedTarget instanceof HTMLTextAreaElement)) keyboard.hide(); };
  const shared = { 'aria-label': label, value, placeholder, maxLength, style: { ...style, boxSizing: 'border-box', borderStyle: 'solid', outline: 'none', resize: 'none' } as CSSProperties, onBlur: blur, autoComplete: 'off' };
  if (multiline) return <KeyboardTextarea {...shared} onChange={e => onChange(e.target.value)} />;
  if (!secure) return <KeyboardInput {...shared} type="text" inputMode={numeric ? 'decimal' : label === 'Email' ? 'email' : 'text'} onChange={e => onChange(e.target.value)} />;
  return <View style={{ position: 'absolute', left: style.left as number, top: style.top as number, width: style.width as number, height: style.height as number }}>
    <KeyboardInput {...shared} style={{ ...shared.style, left: 0, top: 0, paddingRight: 50 }} type={visible ? 'text' : 'password'} onChange={e => onChange(e.target.value)} />
    <Pressable role="button" aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`} onPress={() => setVisible(v => !v)} style={{ position: 'absolute', right: 5, top: 5, width: 43, height: 43, alignItems: 'center', justifyContent: 'center' }}><Icons name={visible ? 'EyeOff' : 'Eye'} size={20} color="#848984" /></Pressable>
  </View>;
}
