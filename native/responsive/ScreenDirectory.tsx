import { View } from 'react-native';
import type { AppRoute } from '../../src/nutrisole/types';
import { colors } from '../../src/nutrisole/extensions/model';
import Icons from '../../src/nutrisole/extensions/Icons.native';
import { T, Header, Screen, Panel, Tap, s } from './components';
import { settingsGroups } from './navigation';

export default function ScreenDirectory({ go, back, action, signedIn }: { go: (route: AppRoute) => void; back: () => void; action: (action: string) => void; signedIn: boolean }) {
  return <Screen route="flow-directory" header={<Header title="Menu & Settings" back={back} />}>
    {settingsGroups.map(group => <View key={group.title} style={{ gap: 9 }}>
      <T size={18} bold color={colors.green}>{group.title}</T>
      <Panel style={{ padding: 0, gap: 0 }}>{group.items.map((item, index) => {
        const signOut = item.route === 'sign-in' && signedIn;
        const label = signOut ? 'Sign out' : item.label;
        return <Tap key={item.label} testID={`menu-${signOut ? 'sign-out' : item.route || item.action}`} label={label} onPress={() => signOut ? action('sign-out') : item.route === 'report-status' ? action('my-reports') : item.route ? go(item.route) : action(item.action!)} style={[s.row, { padding: 15, minHeight: 52, borderTopWidth: index ? .6 : 0, borderColor: colors.border }]}>
          <Icons name={item.icon} size={23} color={colors.green} /><View style={[s.flex, { gap: 5 }]}><T size={16} bold>{label}</T><T size={13} color={colors.muted}>{signOut ? 'End the local demo session' : item.description}</T></View><Icons name="ChevronRight" size={18} color={colors.muted} />
        </Tap>;
      })}</Panel>
    </View>)}
  </Screen>;
}
