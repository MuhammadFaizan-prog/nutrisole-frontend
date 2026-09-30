import { Box, Divider, Txt, Photo, Surface, Glyph, SourceArt, Hit, palette } from './ui';
import type { Profile as ProfileData, Store } from './store';
import type { Sheet } from './types';
import type { SourceArtName } from './sourceArt';

const preferences: { key: keyof ProfileData; label: string; icon: SourceArtName; y: number; fs?: number }[] = [
  { key: 'dietary', label: 'Dietary Preferences', icon: 'profile-dietary', y: 560 },
  { key: 'allergens', label: 'Allergens', icon: 'profile-allergens', y: 652 },
  { key: 'activity', label: 'Activity Preferences', icon: 'profile-activity', y: 742, fs: 21.5 },
  { key: 'mobility', label: 'Mobility Constraints', icon: 'profile-mobility', y: 836 },
  { key: 'glucoseUnit', label: 'Glucose Unit', icon: 'profile-glucose', y: 927 },
  { key: 'timezone', label: 'Timezone', icon: 'profile-timezone', y: 1017 },
];
export default function Profile({ store, back, open }: { store: Store; back: () => void; open: (sheet: Sheet) => void }) {
  const { profile } = store.state;
  function edit(key: keyof ProfileData, label: string) {
    if (key === 'glucoseUnit') return open({ title: 'Glucose Unit', description: 'Choose the display unit for this local demo.', choices: ['mg/dL', 'mmol/L'].map(unit => ({ label: unit, selected: profile.glucoseUnit === unit, action: () => store.update(old => ({ ...old, profile: { ...old.profile, glucoseUnit: unit } })) })) });
    open({ title: label, fields: [{ key, label, value: profile[key] }], save: v => { if (!v[key]?.trim()) return 'Enter a value, or use None for no constraint.'; store.update(old => ({ ...old, profile: { ...old.profile, [key]: v[key].trim() } })); } });
  }
  return <>
    <Photo x={50} y={166} w={760} h={1564} asset="paper-profile" />
    <SourceArt name="profile-back" /><Hit x={68} y={281} w={95} h={85} label="Go back" onPress={back} />
    <Txt x={210} y={291} w={500} fs={38} bold align="center">Profile & Preferences</Txt>
    <Surface x={74} y={364} w={717} h={178} radius={28} texture="warm-card-texture-tile" />
    <Photo x={108} y={386} w={138} h={135} radius={75} asset="alex-avatar" />
    <Txt x={280} y={412} w={435} fs={40} bold maxLines={1}>{profile.name}</Txt>
    <Txt x={280} y={462} w={459} fs={30} color={palette.muted} maxLines={1}>{profile.email}</Txt>
    <SourceArt name="profile-account-chevron" />
    <Hit x={74} y={364} w={717} h={178} label="Edit account" onPress={() => open({ title: 'Your profile', fields: [{ key: 'name', label: 'Name', value: profile.name }, { key: 'email', label: 'Email', value: profile.email }], save: v => { if (!v.name?.trim()) return 'Enter a name.'; if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.email)) return 'Enter a valid email.'; store.update(old => ({ ...old, profile: { ...old.profile, name: v.name.trim(), email: v.email.trim() } })); } })} />
    <Surface x={74} y={560} w={717} h={548} radius={28} texture="warm-card-texture-tile" />
    {preferences.map((p, index) => <Box key={p.key} x={50} y={166} w={760} h={1564}>
      {index > 0 && <Divider x={107} y={p.y} w={683} h={1.1} />}
      <SourceArt name={p.icon} />
      <Txt x={172} y={p.y + 31} w={340} fs={30}>{p.label}</Txt>
      <Txt x={p.key === 'activity' ? 453 : 430} y={p.y + 33} w={p.key === 'activity' ? 311 : 330} fs={p.fs ?? 26} color="#8a8b92" align="right" maxLines={1}>{profile[p.key]}</Txt>
      <Hit x={92} y={p.y + 6} w={684} h={80} label={`Edit ${p.label}`} onPress={() => edit(p.key, p.label)} />
    </Box>)}
    <Surface x={74} y={1123} w={717} h={132} radius={28} texture="warm-card-texture-tile" />
    <SourceArt name="profile-health" />
    <Txt x={185} y={1148} w={486} fs={31}>Connected Health Source</Txt>
    <Txt x={185} y={1193} w={310} fs={31} color={palette.muted}>Apple Health</Txt>
    <Surface x={581} y={1157} w={187} h={63} radius={40} fill="#e9f5e7" border={false} />
    {store.state.connected ? <SourceArt name="profile-connected" /> : <Glyph x={598} y={1179} name="X" size={25} color="#19563c" weight={2.1} />}
    <Txt x={625} y={1175} w={138} fs={26} bold color="#165438">{store.state.connected ? 'Connected' : 'Off'}</Txt>
    <Hit x={74} y={1123} w={717} h={132} label="Manage health connection" onPress={() => open({ title: 'Apple Health', description: 'This is a simulated connection. No HealthKit access or real health data is requested.', choices: [{ label: store.state.connected ? 'Disconnect demo source' : 'Connect demo source', action: () => store.update(old => ({ ...old, connected: !old.connected })) }] })} />
    <Surface x={74} y={1270} w={717} h={142} radius={30} texture="warm-card-texture-tile" />
    <SourceArt name="profile-privacy" />
    <Txt x={178} y={1305} w={546} fs={33}>Privacy & Consent</Txt>
    <Txt x={178} y={1350} w={558} fs={28} color="#81858a">Manage your data and permissions</Txt>
    <SourceArt name="profile-privacy-chevron" />
    <Hit x={74} y={1270} w={717} h={142} label="Privacy and consent" onPress={() => open({ title: 'Privacy & Consent', description: 'Only synthetic demo preferences and meal records are stored on this device. No data is sent to a server.', choices: [{ label: store.state.retainImages ? 'Image retention: on — turn off' : 'Image retention: off — turn on', action: () => store.update(old => ({ ...old, retainImages: !old.retainImages })) }, { label: 'Reset demo data', action: store.reset }] })} />
  </>;
}
