import { useState } from 'react';
import { Box, Divider, Txt, Photo, Surface, SourceArt, Hit, palette } from './ui';
import type { Store } from './store';
import type { Sheet } from './types';
import ProgressRing from './ProgressRing';

const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
export default function WeeklyPlan({ back, open, store }: { back: () => void; open: (sheet: Sheet) => void; store: Store }) {
  const [day, setDay] = useState(0);
  const [tab, setTab] = useState<'Meals' | 'Nutrition'>('Meals');
  const [weekOffset, setWeekOffset] = useState(0);
  const key = `${weekOffset}:${day}:breakfast`;
  const accepted = store.state.accepted.includes(key);
  const replacement = store.state.substitutes[key];
  const feedback = store.state.feedback[key];
  const firstDate = 18 + weekOffset * 7;
  function substitutes() {
    open({ title: 'Choose a substitute', description: 'Choose a meal for this day. These sample meals contain no tree nuts or shellfish.', choices: ['Berry Overnight Oats', 'Apple & Yogurt Bowl'].map(label => ({ label, selected: (replacement || 'Berry Overnight Oats') === label, action: () => store.update(old => ({ ...old, substitutes: { ...old.substitutes, [key]: label } })) })) });
  }
  return <>
    <Photo x={57} y={149} w={749} h={1537} asset="paper-weekly" />
    <SourceArt name="weekly-back" /><Hit x={70} y={270} w={95} h={85} label="Go back" onPress={back} />
    <Txt x={231} y={270} w={400} fs={42} bold align="center">Weekly Plan</Txt>
    <Txt x={231} y={324} w={400} fs={31} color={palette.muted} align="center">{`Mar ${firstDate} – Mar ${firstDate + 6}`}</Txt>
    <SourceArt name="weekly-calendar" />
    <Hit x={695} y={262} w={89} h={91} label="Choose plan week" onPress={() => open({ title: 'Plan week', description: 'Choose a local demonstration week.', choices: [-1, 0, 1].map(offset => ({ label: `Mar ${18 + offset * 7} – Mar ${24 + offset * 7}`, selected: weekOffset === offset, action: () => setWeekOffset(offset) })) })} />
    {days.map((d, i) => <Box key={d} x={57} y={149} w={749} h={1537}>
      <Surface x={81 + i * 102} y={400} w={i === 0 ? 100 : 95} h={101} radius={22} texture={day === i ? 'dark-green-texture-tile' : 'warm-card-texture-tile'} border={false} />
      <Txt x={81 + i * 102} y={418} w={95} fs={28} align="center" color={day === i ? '#fff' : palette.muted}>{d}</Txt>
      <Txt x={81 + i * 102} y={458} w={95} fs={28} align="center" color={day === i ? '#fff' : palette.muted}>{firstDate + i}</Txt>
      <Hit x={81 + i * 102} y={400} w={95} h={101} label={`Select ${d}`} onPress={() => setDay(i)} />
    </Box>)}
    <Surface x={77} y={523} w={709} h={160} radius={29} texture="warm-card-texture-tile" />
    <Txt x={114} y={560} w={178} fs={43} bold align="center">1,650</Txt>
    <Txt x={111} y={616} w={185} fs={31} align="center" color={palette.muted}>cal goal</Txt>
    <Divider x={297} y={557} w={1.4} h={93} />
    {accepted ? <Box x={339} y={560} w={85} h={85} passive><ProgressRing size={85} stroke={13} fraction={1} /></Box> : <Photo x={339} y={560} w={85} h={85} asset="weekly-progress-ring" />}
    <Txt x={444} y={560} w={115} fs={44} bold>{accepted ? '5/5' : '4/5'}</Txt>
    <Txt x={443} y={616} w={113} fs={31} color="#627176">meals</Txt>
    <Divider x={567} y={557} w={1.4} h={93} />
    <Txt x={590} y={560} w={173} fs={43} bold align="center">{accepted ? '100%' : '82%'}</Txt>
    <Txt x={589} y={616} w={174} fs={31} color={palette.muted} align="center">adherence</Txt>
    <Surface x={77} y={706} w={709} h={100} radius={30} texture="gray-track-texture-tile" border={false} />
    <Txt x={88} y={735} w={341} fs={37} bold={tab === 'Meals'} color={tab === 'Meals' ? palette.green : palette.black} align="center">Meals</Txt>
    <Txt x={435} y={735} w={344} fs={37} bold={tab === 'Nutrition'} color={tab === 'Nutrition' ? palette.green : palette.black} align="center">Nutrition</Txt>
    <Box x={tab === 'Meals' ? 89 : 435} y={796} w={339} h={9} style={{ borderRadius: 8, backgroundColor: palette.green }} />
    <Hit x={77} y={706} w={354} h={100} label="Show meals" onPress={() => setTab('Meals')} />
    <Hit x={431} y={706} w={355} h={100} label="Show nutrition" onPress={() => setTab('Nutrition')} />
    {tab === 'Meals' ? <>
      <Surface x={77} y={831} w={709} h={504} radius={30} texture="warm-card-texture-tile" />
      <Txt x={105} y={863} w={401} fs={40} bold>Breakfast</Txt>
      <Txt x={570} y={875} w={190} fs={27} color={palette.muted} align="right">7:00 – 9:00 AM</Txt>
      <Surface x={103} y={932} w={660} h={170} radius={22} texture="warm-card-texture-tile" />
      <Photo x={104} y={932} w={166} h={168} radius={21} asset={replacement === 'Apple & Yogurt Bowl' ? 'apple-thumbnail' : 'berry-oats'} />
      <Txt x={297} y={951} w={459} fs={34} bold>{replacement || 'Berry Overnight Oats'}</Txt>
      <Txt x={297} y={1001} w={460} fs={27} color={palette.muted} line={32}>{replacement === 'Apple & Yogurt Bowl' ? 'Apple, Greek yogurt, oats, chia seeds' : 'Oats, Greek yogurt, berries, chia seeds'}</Txt>
      <Txt x={297} y={1049} w={130} fs={33}><TxtInline bold>320</TxtInline> cal</Txt>
      <Txt x={430} y={1049} w={325} fs={31}>18g P   42g C   10g F</Txt>
      <Surface x={102} y={1121} w={274} h={90} radius={20} texture="dark-green-texture-tile" border={false} />
      <SourceArt name="weekly-accept" />
      <Txt x={accepted ? 196 : 218} y={1147} w={accepted ? 177 : 150} fs={34} color="#fff">{accepted ? 'Accepted' : 'Accept'}</Txt>
      <Hit x={102} y={1121} w={274} h={90} label="Accept breakfast" onPress={() => store.update(old => ({ ...old, accepted: old.accepted.includes(key) ? old.accepted.filter(k => k !== key) : [...old.accepted, key] }))} />
      <Surface x={391} y={1121} w={275} h={90} radius={20} fill="#faf9f5" />
      <SourceArt name="weekly-substitute" />
      <Txt x={498} y={1147} w={168} fs={33}>Substitute</Txt>
      <Hit x={391} y={1121} w={275} h={90} label="Substitute breakfast" onPress={substitutes} />
      <Surface x={680} y={1121} w={83} h={90} radius={20} fill="#fffdf9" />
      <SourceArt name="weekly-more" />
      <Hit x={680} y={1121} w={83} h={90} label="Breakfast options" onPress={() => open({ title: 'Breakfast', description: `${replacement || 'Berry Overnight Oats'} · 320 cal · 18g protein · 42g carbs · 10g fat`, choices: [{ label: 'Change this meal', action: substitutes }, { label: 'Restore suggested meal', action: () => store.update(old => ({ ...old, substitutes: { ...old.substitutes, [key]: 'Berry Overnight Oats' } })) }] })} />
      <Surface x={102} y={1229} w={661} h={84} radius={20} fill="#f8f7f3" />
      <SourceArt name="weekly-feedback" />
      <Txt x={184} y={1257} w={558} fs={28} color="#82878a">{feedback || 'Not a fan? Tell us why...'}</Txt>
      <Hit x={102} y={1229} w={661} h={84} label="Meal feedback" onPress={() => open({ title: 'Tell us what you prefer', fields: [{ key: 'feedback', label: 'Feedback', value: feedback || '', multiline: true }], save: v => { if (!v.feedback?.trim()) return 'Write a short preference before saving.'; store.update(old => ({ ...old, feedback: { ...old.feedback, [key]: v.feedback.trim() } })); } })} />
      <Surface x={77} y={1357} w={709} h={286} radius={31} texture="warm-card-texture-tile" />
      <Txt x={105} y={1389} w={395} fs={40} bold>Lunch</Txt>
      <Txt x={558} y={1400} w={202} fs={27} color={palette.muted} align="right">12:00 – 2:00 PM</Txt>
      <Surface x={103} y={1453} w={660} h={171} radius={22} texture="warm-card-texture-tile" />
      <Photo x={104} y={1453} w={166} h={162} radius={22} asset="chicken-quinoa-bowl" />
      <Txt x={297} y={1475} w={457} fs={33} bold>Grilled Chicken Quinoa Bowl</Txt>
      <Txt x={297} y={1526} w={460} fs={27} color={palette.muted}>Chicken, quinoa, mixed greens, avocado</Txt>
      <Txt x={297} y={1574} w={130} fs={33}><TxtInline bold>420</TxtInline> cal</Txt>
      <Txt x={430} y={1574} w={325} fs={31}>36g P   48g C   14g F</Txt>
      <Hit x={104} y={1453} w={660} h={171} label="Lunch details" onPress={() => open({ title: 'Grilled Chicken Quinoa Bowl', description: 'Chicken, quinoa, mixed greens, avocado. Seeded demo meal: 420 cal, 36 g protein, 48 g carbohydrate, 14 g fat.' })} />
    </> : <>
      <Surface x={77} y={831} w={709} h={720} radius={31} texture="warm-card-texture-tile" />
      <Txt x={111} y={870} w={628} fs={40} bold>Daily nutrition</Txt>
      <Txt x={111} y={928} w={628} fs={30} color={palette.muted}>{days[day]} {firstDate + day} · Seeded meal plan</Txt>
      {[['Calories', '1,650 kcal', '#ff9448'], ['Protein', '96 g', '#929bf2'], ['Carbohydrates', '184 g', '#59ccb9'], ['Fat', '58 g', '#fbd479']].map((item, i) => <Box key={item[0]} x={57} y={149} w={749} h={1537}>
        <Txt x={112} y={1027 + i * 107} w={365} fs={34}>{item[0]}</Txt>
        <Txt x={501} y={1027 + i * 107} w={239} fs={34} bold align="right">{item[1]}</Txt>
        <Box x={112} y={1081 + i * 107} w={624} h={13} style={{ backgroundColor: item[2], borderRadius: 9 }} />
      </Box>)}
    </>}
  </>;
}

import { Text } from './primitives';
function TxtInline({ bold, children }: { bold?: boolean; children: React.ReactNode }) { return <Text style={{ fontFamily: bold ? 'NutriSansBold' : 'NutriSans' }}>{children}</Text>; }
