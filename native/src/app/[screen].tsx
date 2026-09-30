import { Redirect, useLocalSearchParams } from 'expo-router';
import { routes } from '../../../src/nutrisole/NutriSole';
import type { AppRoute as Route } from '../../../src/nutrisole/types';
export default function Screen() {
  const { screen } = useLocalSearchParams<{ screen: string }>();
  return routes.includes(screen as Route) ? null : <Redirect href={{ pathname: '/[screen]', params: { screen: 'home' } }} />;
}
