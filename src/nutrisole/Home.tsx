import { Box, Divider, Txt, Photo, Surface, SourceArt, Hit, palette } from './ui';
import type { Route } from './types';
import type { Store } from './store';
import ProgressRing from './ProgressRing';

export default function Home({ go, store }: { go: (route: Route) => void; store: Store }) {
  const extra = store.state.meals.reduce((n, m) => n + m.calories, 0);
  const count = Math.min(5, 3 + store.state.meals.length);
  const latest = store.state.meals.at(-1);
  return <>
    <Photo x={42} y={38} w={777} h={1737} asset="paper-home" />
    <Txt x={94} y={176} w={570} fs={43} line={52}>Good morning,</Txt>
    <Txt x={94} y={218} w={580} fs={68} line={76} serif bold maxLines={1}>{store.state.profile.name.split(' ')[0]}</Txt>
    <Photo x={693} y={171} w={88} h={87} radius={55} asset="alex-avatar-home" />
    <Hit x={683} y={161} w={108} h={107} label="Open profile" onPress={() => go('profile')} />
    <Surface x={67} y={311} w={730} h={406} radius={38} texture="warm-card-texture-tile" />
    <Txt x={111} y={351} w={430} fs={29} color="#5d6264" style={{ letterSpacing: 0.4 }}>KEEP GOING</Txt>
    <Txt x={112} y={403} w={469} fs={43} bold line={45}>{count === 5 ? 'You’ve reached\nyour meal goal' : `You’re ${5 - count} ${count === 4 ? 'meal' : 'meals'} away\nfrom your goal`}</Txt>
    {count === 3 ? <Photo x={541} y={334} w={214} h={213} asset="home-progress-ring" /> : <Box x={541} y={334} w={214} h={214} passive><ProgressRing size={214} fraction={count / 5} /></Box>}
    <Txt x={577} y={402} w={144} fs={43} bold align="center">{count}/5</Txt>
    <Txt x={577} y={453} w={144} fs={31} align="center" color="#5e6263">meals</Txt>
    {[
      { x: 112, w: 153, value: (1420 + extra).toLocaleString('en-US'), label: 'calories', color: '#e75212', bar: '#ff9448', progress: 106 },
      { x: 302, w: 135, value: '82g', label: 'protein', color: '#7780bd', bar: '#98a0ed', progress: 78 },
      { x: 478, w: 132, value: `${48 + Math.round(store.state.meals.reduce((n, m) => n + m.grams / 182 * 25, 0))}g`, label: 'carbs', color: '#467f79', bar: '#5fcbb9', progress: 84 },
      { x: 650, w: 111, value: '62g', label: 'fat', color: '#bb882d', bar: '#fbd47d', progress: 62 },
    ].map((m, index) => <Box key={m.label} x={42} y={38} w={777} h={1737}>
      {index > 0 && <Divider x={m.x - 37} y={583} w={1.3} h={111} />}
      <Txt x={m.x - 4} y={577} w={m.w} fs={45} bold>{m.value}</Txt>
      <Txt x={m.x + 2} y={633} w={m.w} fs={30} color={m.color}>{m.label}</Txt>
      <Box x={m.x + 4} y={677} w={index === 0 ? 108 : 98} h={17} style={{ backgroundColor: m.bar, opacity: 0.25, borderRadius: 12 }} />
      <Box x={m.x + 4} y={677} w={m.progress} h={17} style={{ backgroundColor: m.bar, borderRadius: 12 }} />
    </Box>)}
    <Surface x={67} y={740} w={730} h={218} radius={41} texture="dark-green-scan-texture-tile" border={false} />
    <SourceArt name="home-scan-camera" radius={86} />
    <Txt x={334} y={798} w={370} fs={46} bold color="#fff">Scan Food</Txt>
    <Txt x={334} y={859} w={406} fs={34} color="#f2f5ea">Instant nutrition insights</Txt>
    <SourceArt name="home-scan-chevron" />
    <Hit x={67} y={740} w={730} h={218} label="Scan food" onPress={() => go('scan')} />
    <Surface x={67} y={980} w={360} h={226} radius={39} texture="pale-green-texture-tile" border={false} />
    <SourceArt name="home-plan-calendar" />
    <Txt x={111} y={1090} w={260} fs={35} bold>View Plan</Txt>
    <Txt x={112} y={1139} w={310} fs={30} color="#577060">Meals for your goals</Txt>
    <SourceArt name="home-plan-chevron" />
    <Hit x={67} y={980} w={360} h={226} label="View plan" onPress={() => go('weekly-plan')} />
    <Surface x={442} y={980} w={355} h={226} radius={39} texture="lavender-texture-tile" border={false} />
    <SourceArt name="home-health-bars" />
    <Txt x={487} y={1090} w={230} fs={35} bold>Health</Txt>
    <Txt x={488} y={1139} w={291} fs={30} color="#5c6b9f">Trends & insights</Txt>
    <SourceArt name="home-health-chevron" />
    <Hit x={442} y={980} w={355} h={226} label="Open health" onPress={() => go('health')} />
    <Surface x={67} y={1228} w={730} h={384} radius={37} texture="warm-card-texture-tile" />
    <Txt x={96} y={1250} w={510} fs={39} bold>Recent Scans</Txt>
    <Txt x={655} y={1258} w={113} fs={30} color={palette.green}>See all</Txt>
    <SourceArt name="home-see-all-chevron" />
    <Hit x={645} y={1238} w={139} h={67} label="See all scans" onPress={() => go('history')} />
    <Divider x={97} y={1306} w={666} h={1} />
    <Photo x={96} y={1321} w={122} h={116} radius={18} asset="apple-thumbnail-home" />
    <Txt x={244} y={1327} w={433} fs={33} bold>Apple</Txt>
    <Txt x={244} y={1370} w={460} fs={29} color={palette.muted}>{latest ? `${Math.round(latest.grams)} g (confirmed)` : '1 medium (confirmed)'}</Txt>
    <Txt x={244} y={1405} w={325} fs={33} bold>{latest?.calories ?? 95} cal</Txt>
    <Txt x={626} y={1333} w={138} fs={28} color="#777a78" align="right">{latest ? 'Just now' : '12:24 PM'}</Txt>
    <Hit x={96} y={1319} w={667} h={130} label="Review apple scan" onPress={() => go('log-meal')} />
    <Divider x={96} y={1457} w={667} h={1.1} />
    <Photo x={96} y={1471} w={122} h={118} radius={20} asset="chicken-bowl-home" />
    <Txt x={244} y={1477} w={507} fs={32} bold>Grilled Chicken Bowl</Txt>
    <Txt x={244} y={1519} w={485} fs={29} color={palette.muted}>Chicken, rice, veggies</Txt>
    <Txt x={244} y={1554} w={295} fs={33} bold>420 cal</Txt>
    <Txt x={642} y={1481} w={122} fs={27} color={palette.muted} align="right">Yesterday</Txt>
    <Hit x={96} y={1460} w={667} h={140} label="Review chicken bowl" onPress={() => go('history')} />
    <Surface x={43} y={1627} w={775} h={147} radius={0} fill="#fffdf7" />
    {[
      { x: 97, label: 'Home', route: 'home' as const, icon: 'home-nav-home' as const },
      { x: 244, label: 'Plan', route: 'weekly-plan' as const, icon: 'home-nav-plan' as const },
      { x: 551, label: 'Health', route: 'health' as const, icon: 'home-nav-health' as const },
      { x: 697, label: 'Profile', route: 'profile' as const, icon: 'home-nav-profile' as const },
    ].map(tab => <Box key={tab.label} x={42} y={38} w={777} h={1737}>
      <SourceArt name={tab.icon} />
      <Txt x={tab.x - 6} y={1710} w={90} fs={26} align="center" color={tab.route === 'home' ? palette.green : '#676a6a'} bold={tab.route === 'home'}>{tab.label}</Txt>
      <Hit x={tab.x - 12} y={1642} w={110} h={116} label={`Navigate ${tab.label}`} onPress={() => go(tab.route)} />
    </Box>)}
    <SourceArt name="home-nav-camera" radius={80} />
    <Hit x={355} y={1584} w={151} h={151} label="Open camera" onPress={() => go('scan')} />
  </>;
}
