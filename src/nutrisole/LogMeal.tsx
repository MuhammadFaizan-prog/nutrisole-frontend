import { useRef, useState } from 'react';
import { Box, Txt, Photo, Surface, SourceArt, Hit, Primary, palette } from './ui';
import { edibleMass, energyForMass, type PortionMode } from './domain';
import type { Store } from './store';
import type { Sheet } from './types';

export default function LogMeal({ back, home, store, open }: { back: () => void; home: () => void; store: Store; open: (sheet: Sheet) => void }) {
  const [mode, setMode] = useState<PortionMode>('amount');
  const [quantity, setQuantity] = useState(1);
  const [weight, setWeight] = useState(182);
  const [size, setSize] = useState<'small' | 'medium' | 'large'>('medium');
  const submissionKey = useRef(`portion-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const submitted = useRef(false);
  const mass = edibleMass(mode, mode === 'weight' ? weight : quantity, size);
  const calories = energyForMass(mass);
  const save = (kind: 'consumed' | 'draft') => {
    if (submitted.current) return;
    submitted.current = true;
    store.saveMeal({ id: submissionKey.current, submissionKey: submissionKey.current, grams: mass, calories, createdAt: new Date().toISOString() }, kind);
    home();
  };
  const editWeight = () => open({ title: 'Edible weight', description: 'Enter the apple portion in grams. This is a demo estimate based on 95 cal per 182 g.', fields: [{ key: 'grams', label: 'Weight in grams', value: String(weight), numeric: true }], save: v => {
    const grams = Number(v.grams);
    if (!Number.isFinite(grams) || grams <= 0 || grams > 10000) return 'Enter a weight greater than 0 and at most 10,000 g.';
    setWeight(grams);
  } });
  const editSize = () => open({ title: 'Apple size', description: 'Demo edible weights: small 149 g, medium 182 g, large 223 g.', choices: (['small', 'medium', 'large'] as const).map(s => ({ label: `${s[0].toUpperCase()}${s.slice(1)} apple`, selected: size === s, action: () => setSize(s) })) });
  return <>
    <Photo x={55} y={120} w={750} h={1604} asset="warm-background-tile" />
    <SourceArt name="log-back" /><Hit x={75} y={237} w={95} h={85} label="Go back" onPress={back} />
    <Txt x={248} y={248} w={367} fs={44} bold align="center">Log Meal</Txt>
    <Surface x={77} y={333} w={708} h={193} radius={37} texture="warm-card-texture-tile" border={false} />
    <Photo x={103} y={352} w={175} h={153} radius={31} asset="apple-thumbnail" />
    <Txt x={315} y={384} w={350} fs={37} bold>Apple</Txt>
    <Txt x={315} y={433} w={411} fs={31} color={palette.muted}>95 cal per medium (182 g)</Txt>
    <SourceArt name="log-info" />
    <Hit x={686} y={383} w={83} h={90} label="Nutrition information" onPress={() => open({ title: 'Apple nutrition', description: 'Demo basis: 95 calories per medium apple, with an edible portion of 182 g. Values are estimates. A photo does not measure the weight of your food.' })} />
    <Txt x={92} y={566} w={625} fs={44} bold>Confirm portion</Txt>
    <Txt x={92} y={626} w={675} fs={34} line={40} color={palette.muted}>{'Adjust the amount you plan to eat.\nThis helps us log your meal accurately.'}</Txt>
    <Surface x={91} y={744} w={681} h={87} radius={47} texture="gray-track-texture-tile" border={false} />
    {(['amount', 'weight', 'size'] as const).map((m, i) => <Box key={m} x={55} y={120} w={750} h={1604}>
      {mode === m && <Surface x={91 + i * 227} y={744} w={233} h={87} radius={47} texture="dark-green-texture-tile" border={false} />}
      <Txt x={91 + i * 227} y={770} w={227} fs={32} align="center" color={mode === m ? '#fff' : palette.muted}>{`By ${m}`}</Txt>
      <Hit x={91 + i * 227} y={744} w={227} h={87} label={`Portion by ${m}`} onPress={() => { setMode(m); if (m === 'weight') editWeight(); if (m === 'size') editSize(); }} />
    </Box>)}
    <SourceArt name="log-minus" />
    <Hit x={82} y={878} w={96} h={96} label="Decrease portion" disabled={mode !== 'weight' && quantity <= 1} onPress={() => mode === 'weight' ? setWeight(v => Math.max(1, v - 10)) : setQuantity(v => Math.max(1, v - 1))} />
    <Txt x={187} y={889} w={90} fs={64} bold align="center">{mode === 'weight' ? weight : quantity}</Txt>
    <SourceArt name="log-plus" />
    <Hit x={288} y={878} w={96} h={96} label="Increase portion" onPress={() => mode === 'weight' ? setWeight(v => Math.min(10000, v + 10)) : setQuantity(v => Math.min(50, v + 1))} />
    <Txt x={418} y={889} w={363} fs={37} bold>{mode === 'weight' ? 'grams' : `${size} apple${quantity > 1 ? 's' : ''}`}</Txt>
    <Txt x={418} y={935} w={373} fs={29} color={palette.muted}>{`(about ${Math.round(mass)} g, edible portion)`}</Txt>
    <Hit x={404} y={880} w={370} h={100} label="Edit portion details" onPress={mode === 'weight' ? editWeight : editSize} />
    <Surface x={81} y={1015} w={699} h={195} radius={40} texture="pale-green-estimate-texture-tile" border={false} />
    <SourceArt name="log-estimate-apple" />
    <Txt x={178} y={1049} w={550} fs={40} bold color="#123e35">≈ {calories} calories</Txt>
    <Txt x={178} y={1102} w={574} fs={31} color="#51646a">{`Estimated for ${mode === 'weight' ? `${weight} g of apple` : `${quantity} ${size} apple${quantity > 1 ? 's' : ''}`}`}</Txt>
    <Txt x={178} y={1146} w={574} fs={31} color="#51646a">Values are estimates.</Txt>
    <Primary x={87} y={1237} w={688} h={115} text="Log Meal" label="Confirm log meal" onPress={() => save('consumed')} />
    <Txt x={230} y={1407} w={400} fs={42} align="center" bold color="#103e32">Save for later</Txt>
    <Hit x={230} y={1389} w={400} h={90} label="Save for later" onPress={() => save('draft')} />
  </>;
}
