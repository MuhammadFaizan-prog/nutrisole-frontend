import { View } from 'react-native';
import Icons from '../../src/nutrisole/extensions/Icons.native';
import { colors } from '../../src/nutrisole/extensions/model';
import type { AppRoute } from '../../src/nutrisole/types';
import { T, Panel, Tap, s } from './components';
import { taskLinks } from './navigation';

export default function TaskLinks({ route, go }: { route: AppRoute; go: (route: AppRoute) => void }) {
  const items = taskLinks(route);
  if (!items.length) return null;
  return <View style={{ gap: 9, marginTop: 12 }}><T size={18} bold color={colors.green}>{route === 'weekly-plan' ? 'Plan tools' : 'Related tools'}</T><Panel style={{ padding: 0, gap: 0 }}>
    {items.map((item, index) => <Tap key={item.route} label={item.label} testID={`task-${item.route}`} onPress={() => go(item.route)} style={[s.row, { padding: 14, minHeight: 52, borderTopWidth: index ? .6 : 0, borderColor: colors.border }]}>
      <Icons name={item.icon} color={colors.green} size={23} /><View style={[s.flex, { gap: 5 }]}><T size={16} bold>{item.label}</T>{item.description && <T size={13} color={colors.muted}>{item.description}</T>}</View><Icons name="ChevronRight" size={18} color={colors.muted} />
    </Tap>)}
  </Panel></View>;
}
