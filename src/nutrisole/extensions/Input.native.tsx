import { TextInput, View, Pressable, type TextStyle } from 'react-native';
import { useState } from 'react';
import Icons from './Icons';
export type InputProps = { label: string; value: string; placeholder?: string; secure?: boolean; numeric?: boolean; multiline?: boolean; maxLength?: number; onChange: (value: string) => void; style: Record<string, unknown> };
export default function Input({ label, value, placeholder, secure, numeric, multiline, maxLength = 100, onChange, style }: InputProps) {
  const [visible, setVisible] = useState(false);
  // Compact source-design fields are shorter than two 16px insets plus a line.
  // Keep the same outer rectangle while leaving a full line available to Android.
  const inputStyle = { ...style, paddingVertical: Math.min(16, Math.max(0, (Number(style.height) - Number(style.lineHeight || 21)) / 2)), includeFontPadding: false, textAlignVertical: multiline ? 'top' : 'center' } as TextStyle;
  // Native focus changes manage the keyboard. Dismissing on the previous field's
  // blur event also blurs the newly focused field and can discard typed characters.
  const input = <TextInput accessibilityLabel={label} value={value} placeholder={placeholder} placeholderTextColor="#8c8f8d" secureTextEntry={secure && !visible} multiline={multiline} keyboardType={numeric ? 'decimal-pad' : label === 'Email' ? 'email-address' : 'default'} autoCapitalize={label === 'Name' ? 'words' : 'none'} autoCorrect={false} autoComplete="off" maxLength={maxLength} onChangeText={onChange} underlineColorAndroid="transparent" style={secure ? { ...inputStyle, left: 0, top: 0, paddingRight: 50 } : inputStyle} />;
  return secure ? <View style={{ position: 'absolute', left: style.left as number, top: style.top as number, width: style.width as number, height: style.height as number }}>{input}<Pressable accessibilityRole="button" accessibilityLabel={visible ? 'Hide password' : 'Show password'} onPress={() => setVisible(v => !v)} style={{ position: 'absolute', right: 5, top: 5, width: 43, height: 43, alignItems: 'center', justifyContent: 'center' }}><Icons name={visible ? 'EyeOff' : 'Eye'} size={20} color="#848984" /></Pressable></View> : input;
}
