import { useEffect, useState, type PropsWithChildren } from 'react';
import { useRouter, usePathname } from 'expo-router';
import { SafeAreaView, View, Text, TextInput, Modal, Pressable, KeyboardAvoidingView, ScrollView, Keyboard, Platform, useWindowDimensions, StyleSheet } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useFonts } from 'expo-font';
import { Roboto_400Regular } from '@expo-google-fonts/roboto/400Regular';
import { Roboto_600SemiBold } from '@expo-google-fonts/roboto/600SemiBold';
import { LibreCaslonDisplay_400Regular } from '@expo-google-fonts/libre-caslon-display/400Regular';
import NutriSole, { routes } from '../src/nutrisole/NutriSole';
import type { AppRoute as Route, Sheet } from '../src/nutrisole/types';

export default function App({ children }: PropsWithChildren) {
  const router = useRouter();
  const pathname = usePathname().slice(1);
  const requestedRoute: Route = routes.includes(pathname as Route) ? pathname as Route : 'onboarding';
  const { width, height } = useWindowDimensions();
  const [loaded] = useFonts({ NutriSans: Roboto_400Regular, NutriSansBold: Roboto_600SemiBold, NutriSerif: LibreCaslonDisplay_400Regular, NutriSerifBold: require('../assets/fonts/LibreCaslonText-Bold.ttf'), NutriSerifText: require('../assets/fonts/LibreCaslonText-Regular.ttf') });
  const [currentRoute, setCurrentRoute] = useState('onboarding');
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  useEffect(() => { setValues(Object.fromEntries((sheet?.fields || []).map(f => [f.key, f.value]))); setError(''); }, [sheet]);
  if (!loaded) return <View style={{ flex: 1, backgroundColor: '#faf8f1' }} />;
  const close = () => { Keyboard.dismiss(); setSheet(null); };
  const save = () => { const message = sheet?.save?.(values); if (message) setError(message); else close(); };
  return <View style={{ flex: 1, backgroundColor: '#faf8f1' }}>
    <View style={{ height: 0, overflow: 'hidden' }}>{children}</View>
    <StatusBar style={currentRoute === 'scan' ? 'light' : 'dark'} />
    <NutriSole width={width} height={height} requestedRoute={requestedRoute} navigation={{ go: next => router.push({ pathname: '/[screen]', params: { screen: next } }), back: () => router.canGoBack() ? router.back() : router.replace({ pathname: '/[screen]', params: { screen: 'home' } }), home: () => { router.dismissAll(); router.replace({ pathname: '/[screen]', params: { screen: 'home' } }); } }} open={next => { Keyboard.dismiss(); setSheet(next); }} routeChanged={setCurrentRoute} beforeNavigate={() => Keyboard.dismiss()} />
    <Modal visible={Boolean(sheet)} animationType="slide" transparent onRequestClose={close}>
      <KeyboardAvoidingView style={styles.overlay} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <Pressable style={StyleSheet.absoluteFill} onPress={close} accessibilityLabel="Dismiss sheet" />
        <SafeAreaView style={styles.sheet}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 24, gap: 14 }}>
          <Text style={styles.title}>{sheet?.title}</Text>
          {sheet?.description && <Text style={styles.description}>{sheet.description}</Text>}
          {sheet?.fields?.map(f => <View key={f.key} style={{ gap: 8 }}><Text style={styles.label}>{f.label}</Text><TextInput accessibilityLabel={f.label} style={[styles.input, f.multiline && { minHeight: 90 }]} value={values[f.key] || ''} onChangeText={value => setValues(v => ({ ...v, [f.key]: value }))} multiline={f.multiline} keyboardType={f.numeric ? 'decimal-pad' : 'default'} maxLength={f.multiline ? 300 : 100} /></View>)}
          {sheet?.choices?.map(choice => <Pressable key={choice.label} style={styles.choice} accessibilityRole="button" onPress={() => { close(); choice.action(); }}><Text style={styles.label}>{choice.label}{choice.selected ? ' ✓' : ''}</Text></Pressable>)}
          {error && <Text accessibilityRole="alert" style={{ color: '#a52d22' }}>{error}</Text>}
          {sheet?.save && <Pressable style={styles.save} accessibilityRole="button" onPress={save}><Text style={styles.saveText}>Save</Text></Pressable>}
          <Pressable onPress={close} accessibilityRole="button" style={{ padding: 15 }}><Text style={[styles.label, { textAlign: 'center' }]}>{sheet?.save ? 'Cancel' : 'Close'}</Text></Pressable>
        </ScrollView></SafeAreaView>
      </KeyboardAvoidingView>
    </Modal>
  </View>;
}
const styles = StyleSheet.create({
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
