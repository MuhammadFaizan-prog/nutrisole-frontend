import { Back, Box, Divider, Txt, Photo, Surface, Glyph, Hit, palette } from './ui';
import type { Store } from './store';
import type { Route, Sheet } from './types';

export default function Secondary({ route, back, go, store, open }: { route: 'health' | 'history'; back: () => void; go: (r: Route) => void; store: Store; open: (s: Sheet) => void }) {
  const health = route === 'health';
  return <>
    <Photo x={55} y={120} w={750} h={1604} asset="warm-background-tile" />
    <Back y={247} onPress={back} />
    <Txt x={245} y={249} w={370} fs={42} bold align="center">{health ? 'Health' : 'Scan History'}</Txt>
    <Surface x={78} y={344} w={706} h={195} radius={33} texture="pale-green-texture-tile" border={false} />
    <Glyph x={114} y={380} name={health ? 'Heart' : 'Camera'} size={50} color={palette.green} />
    <Txt x={185} y={376} w={566} fs={38} bold color={palette.green}>{health ? 'Your daily picture' : 'Recent food scans'}</Txt>
    <Txt x={114} y={450} w={610} fs={30} color={palette.muted}>{health ? 'Meal records and plan progress, in one place.' : 'Review your food and confirmed portions.'}</Txt>
    {health ? <>
      <Surface x={78} y={574} w={706} h={248} radius={32} texture="warm-card-texture-tile" />
      <Txt x={114} y={615} w={600} fs={37} bold>Meals logged</Txt>
      <Txt x={114} y={675} w={600} fs={60} bold color={palette.green}>{store.state.meals.length}</Txt>
      <Txt x={114} y={757} w={600} fs={28} color={palette.muted}>New records in this local demo</Txt>
      <Surface x={78} y={858} w={706} h={233} radius={32} texture="warm-card-texture-tile" />
      <Txt x={114} y={899} w={600} fs={37} bold>Glucose history</Txt>
      <Txt x={114} y={964} w={600} fs={31} color={palette.muted}>No readings yet</Txt>
      <Txt x={114} y={1013} w={600} fs={28} color={palette.muted}>Real health data is outside this frontend demo.</Txt>
      <Hit x={78} y={858} w={706} h={233} label="Explain health data" onPress={() => open({ title: 'Health data', description: 'This frontend uses synthetic fixtures only. No glucose values or real health records are imported or inferred.' })} />
    </> : <>
      {[
        { photo: 'apple-thumbnail', name: 'Apple', detail: '1 medium (confirmed)', calories: '95 cal', action: () => go('log-meal') },
        { photo: 'chicken-bowl-home', name: 'Grilled Chicken Bowl', detail: 'Chicken, rice, veggies', calories: '420 cal', action: () => open({ title: 'Grilled Chicken Bowl', description: 'A seeded scan from Yesterday. Demo estimate: 420 calories.' }) },
        ...store.state.meals.slice().reverse().map(meal => ({ photo: 'apple-thumbnail', name: 'Apple · Logged', detail: `${Math.round(meal.grams)} g, edible portion`, calories: `${meal.calories} cal`, action: () => open({ title: 'Logged meal', description: `${Math.round(meal.grams)} g apple · ${meal.calories} calories. Saved locally in this demo.` }) })),
        ...store.state.drafts.map(meal => ({ photo: 'apple-thumbnail', name: 'Apple · Saved for later', detail: `${Math.round(meal.grams)} g, not consumed`, calories: `${meal.calories} cal`, action: () => open({ title: 'Saved apple portion', description: `${Math.round(meal.grams)} g, edible portion · ${meal.calories} calories`, choices: [{ label: 'Log this saved portion', action: () => store.saveMeal(meal, 'consumed') }] }) })),
      ].slice(0, 5).map((meal, i) => <Box key={i} x={55} y={120} w={750} h={1604}>
        <Surface x={78} y={574 + i * 197} w={706} h={173} radius={28} texture="warm-card-texture-tile" />
        <Photo x={100} y={598 + i * 197} w={129} h={123} radius={23} asset={meal.photo} />
        <Txt x={256} y={597 + i * 197} w={480} fs={33} bold>{meal.name}</Txt>
        <Txt x={256} y={642 + i * 197} w={480} fs={28} color={palette.muted}>{meal.detail}</Txt>
        <Txt x={256} y={687 + i * 197} w={480} fs={29} bold>{meal.calories}</Txt>
        <Hit x={78} y={574 + i * 197} w={706} h={173} label={`Open ${meal.name} ${i}`} onPress={meal.action} />
      </Box>)}
    </>}
  </>;
}
