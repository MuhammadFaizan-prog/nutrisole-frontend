import { Pressable as WebPressable } from 'react-native-web';
import type { ComponentType, PropsWithChildren } from 'react';
export { View, Text, Image } from 'react-native-web';
// RN Web supports role/aria-label; its community declaration currently omits them.
export const Pressable = WebPressable as unknown as ComponentType<PropsWithChildren<{
  role?: 'button'; 'aria-label'?: string; testID?: string; disabled?: boolean; onPress?: () => void;
  style?: unknown;
}>>;
