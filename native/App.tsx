import { useEffect, useState } from 'react';
import { View, Text, TextInput, Modal, Pressable, ScrollView, Keyboard, Linking, StatusBar, StyleSheet } from 'react-native';
import { SafeAreaProvider, SafeAreaView, initialWindowMetrics } from 'react-native-safe-area-context';
import NutriSole, { routes } from './responsive/NutriSole';
import { FrameProvider } from './responsive/components';
import KeyboardFrame from './responsive/KeyboardFrame';
import type { AppRoute as Route, Sheet } from '../src/nutrisole/types';
import { routeFromURL } from './deepLinks';
import { withNativeDestinations } from './nativeMenu';

export default function App() {
  const [requestedRoute, setRequestedRoute] = useState<Route>('onboarding');
  const [navigationToken, setNavigationToken] = useState(0);
  const [requestedIntent, setRequestedIntent] = useState<'reset' | 'push'>('reset');
  const [currentRoute, setCurrentRoute] = useState('onboarding');
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  useEffect(() => {
    const openLink = (url: string | null) => {
      const next = routeFromURL(url, routes);
      if (next) { Keyboard.dismiss(); setSheet(null); setRequestedIntent('reset'); setRequestedRoute(next); setNavigationToken(token => token + 1); }
    };
    Linking.getInitialURL().then(openLink).catch(() => {});
    const subscription = Linking.addEventListener('url', event => openLink(event.url));
    return () => subscription.remove();
  }, []);
  useEffect(() => { setValues(Object.fromEntries((sheet?.fields || []).map(f => [f.key, f.value]))); setError(''); }, [sheet]);
  const close = () => { Keyboard.dismiss(); setSheet(null); };
  const save = () => { const message = sheet?.save?.(values); if (message) setError(message); else close(); };
  const openScreen = (next: Route) => { close(); setRequestedIntent('push'); setRequestedRoute(next); setNavigationToken(token => token + 1); };
  return <SafeAreaProvider initialMetrics={initialWindowMetrics}><View style={[styles.app, currentRoute === 'scan' && { backgroundColor: '#111' }]}>
    <StatusBar barStyle={currentRoute === 'scan' ? 'light-content' : 'dark-content'} />
    <SafeAreaView style={styles.flex} edges={['top', 'left', 'right', 'bottom']}><KeyboardFrame style={styles.flex}><FrameProvider>
      <NutriSole requestedRoute={requestedRoute} requestedIntent={requestedIntent} navigationToken={navigationToken} open={next => { Keyboard.dismiss(); setSheet(withNativeDestinations(next, openScreen)); }} routeChanged={setCurrentRoute} />
    </FrameProvider></KeyboardFrame></SafeAreaView>
    <Modal visible={Boolean(sheet)} animationType="slide" transparent onRequestClose={close}>
      <KeyboardFrame style={styles.overlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={close} accessibilityLabel="Dismiss sheet" />
        <SafeAreaView style={styles.sheet} edges={['bottom', 'left', 'right']}><ScrollView keyboardShouldPersistTaps="handled" keyboardDismissMode="on-drag" contentContainerStyle={styles.sheetContent}>
          <Text style={styles.title}>{sheet?.title}</Text>
          {sheet?.description && <Text style={styles.description}>{sheet.description}</Text>}
          {sheet?.fields?.map(f => <View key={f.key} style={styles.field}><Text style={styles.label}>{f.label}</Text>{f.key === 'json' ? <Text selectable accessibilityLabel={f.label} style={[styles.input, styles.multiline]}>{values[f.key] || ''}</Text> : <TextInput accessibilityLabel={f.label} style={[styles.input, f.multiline && styles.multiline]} value={values[f.key] || ''} onChangeText={value => setValues(v => ({ ...v, [f.key]: value }))} multiline={f.multiline} keyboardType={f.numeric ? 'decimal-pad' : 'default'} maxLength={f.multiline ? 300 : 100} />}</View>)}
          {sheet?.choices?.map(choice => <Pressable key={choice.label} style={styles.choice} accessibilityRole="button" onPress={() => { close(); choice.action(); }}><Text style={styles.label}>{choice.label}{choice.selected ? ' ✓' : ''}</Text></Pressable>)}
          {error && <Text accessibilityRole="alert" style={styles.error}>{error}</Text>}
          {sheet?.save && <Pressable style={styles.save} accessibilityRole="button" onPress={save}><Text style={styles.saveText}>Save</Text></Pressable>}
          <Pressable onPress={close} accessibilityRole="button" style={styles.cancel}><Text style={[styles.label, styles.center]}>{sheet?.save ? 'Cancel' : 'Close'}</Text></Pressable>
        </ScrollView></SafeAreaView>
      </KeyboardFrame>
    </Modal>
  </View></SafeAreaProvider>;
}
const styles = StyleSheet.create({
  flex: { flex: 1 },
  app: { flex: 1, backgroundColor: '#faf8f1' },
  sheetContent: { padding: 24, gap: 14 },
  field: { gap: 8 },
  multiline: { minHeight: 90 },
  error: { color: '#a52d22' },
  cancel: { padding: 15 },
  center: { textAlign: 'center' },
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: '#0005' },
  sheet: { maxHeight: '82%', backgroundColor: '#fffdf8', borderTopLeftRadius: 28, borderTopRightRadius: 28 },
  title: { fontFamily: 'NutriSansBold', fontSize: 24, color: '#183e2d' },
  description: { fontFamily: 'NutriSans', fontSize: 15, color: '#627065', lineHeight: 22 },
  label: { fontFamily: 'NutriSans', color: '#234e36', fontSize: 16 },
  input: { fontFamily: 'NutriSans', borderWidth: 1, borderColor: '#dce2d8', backgroundColor: '#fafbf6', borderRadius: 12, padding: 14, fontSize: 16 },
  choice: { borderWidth: 1, borderColor: '#dce2d8', borderRadius: 12, backgroundColor: '#f5f8f0', padding: 14 },
  save: { backgroundColor: '#194a32', borderRadius: 14, padding: 15 },
  saveText: { fontFamily: 'NutriSansBold', color: '#fff', fontSize: 16, textAlign: 'center' },
});
