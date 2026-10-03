import type { PropsWithChildren } from 'react';
import { KeyboardAvoidingView, Platform, type StyleProp, type ViewStyle } from 'react-native';

/** Android edge-to-edge windows can leave adjustResize content behind the IME. */
export default function KeyboardFrame({ children, style }: PropsWithChildren<{ style: StyleProp<ViewStyle> }>) {
  // frame.y already includes the outer safe area's Yoga padding.
  return <KeyboardAvoidingView style={style} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>{children}</KeyboardAvoidingView>;
}
