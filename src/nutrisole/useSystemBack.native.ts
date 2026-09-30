import { useEffect } from 'react';
import { BackHandler } from 'react-native';
export function useSystemBack(back: () => void, enabled: boolean) {
  useEffect(() => {
    const listener = BackHandler.addEventListener('hardwareBackPress', () => {
      if (!enabled) return false;
      back();
      return true;
    });
    return () => listener.remove();
  }, [back, enabled]);
}
