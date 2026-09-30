import AsyncStorage from '@react-native-async-storage/async-storage';
export const storage = {
  async get(): Promise<string | null> { try { return await AsyncStorage.getItem('nutrisole.demo.v1'); } catch { return null; } },
  async set(value: string): Promise<void> { try { await AsyncStorage.setItem('nutrisole.demo.v1', value); } catch { /* Keep session usable on storage failure. */ } },
};
