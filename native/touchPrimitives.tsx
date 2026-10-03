import { forwardRef, type ElementRef } from 'react';
import { View as NativeView, type ViewProps } from 'react-native';

export { Text, Image, Pressable } from 'react-native';

// Keep transparent layout groups in the native hierarchy. Fabric flattening of
// overlapping box-none groups otherwise prevents earlier sibling buttons from
// receiving physical touches, even though accessibility lists those buttons.
// Positions, children and drawing styles remain the shared screen's own props.
export const View = forwardRef<ElementRef<typeof NativeView>, ViewProps>(function TouchView(props, ref) {
  return <NativeView {...props} ref={ref} collapsable={props.pointerEvents === 'box-none' ? false : props.collapsable} />;
});
