import { View } from 'react-native';
import { House, NotebookText, Heart, UserRound } from 'lucide-react-native';
import type { AppRoute } from '../../src/nutrisole/types';
import { colors } from '../../src/nutrisole/extensions/model';
import { Art, T, Tap, useFrame, s } from './components';
import { largeTextLayout } from './metrics';
import { primaryTabs, sectionForRoute } from './navigation';

export default function TabBar({ route, navigate }: { route: AppRoute; navigate: (route: AppRoute) => void }) {
  const { width, fontScale } = useFrame();
  const layout = largeTextLayout(width, fontScale);
  const section = sectionForRoute(route);
  return <View testID={`navigation-${route}`} style={[s.footer, s.row, { gap: 0, paddingBottom: 5, alignItems: 'flex-end', flexWrap: layout.expanded ? 'wrap' : 'nowrap' }]}>
    {primaryTabs.map(tab => {
      const active = section === tab.route;
      const color = active ? colors.green : '#676a6a';
      const Glyph = tab.label === 'Home' ? House : tab.label === 'Plan' ? NotebookText : tab.label === 'Health' ? Heart : UserRound;
      return <Tap key={tab.route} label={tab.label === 'Scan' ? 'Open camera' : `Navigate ${tab.label}`} testID={`tab-${tab.route}`} onPress={() => navigate(tab.route)} style={{ flexGrow: 1, flexBasis: layout.expanded ? `${100 / layout.navigationColumns}%` : 0, minWidth: layout.expanded ? 80 : 0, alignItems: 'center', gap: 5, paddingTop: 3, minHeight: 65 }}>
        {tab.label === 'Scan' ? <Art name="home-nav-camera" size={70} /> : tab.label === 'Home' && active ? <Art name="home-nav-home" size={24} /> : <Glyph size={24} color={color} strokeWidth={1.7} />}
        {tab.label !== 'Scan' && <T size={12} bold={active} color={color} style={{ textAlign: 'center', width: '100%' }}>{tab.label}</T>}
      </Tap>;
    })}
  </View>;
}
