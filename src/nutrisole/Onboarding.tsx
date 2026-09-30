import { Box, Txt, Photo, Surface, SourceArt, Hit, palette } from './ui';
import ScenePhoto from './ScenePhoto';

export default function Onboarding({ home }: { home: () => void }) {
  return <>
    <Photo x={38} y={38} w={786} h={1748} asset="paper-onboarding-calibrated" />
    <Photo x={92} y={174} w={63} h={80} asset="leaf-brand-mark" mode="contain" />
    <Txt x={164} y={183} w={340} fs={65} serif>NutriSole</Txt>
    <Txt x={709} y={175} w={90} fs={40}>Skip</Txt><Hit x={690} y={150} w={111} h={90} label="Skip onboarding" onPress={home} />
    <Txt x={104} y={284} w={745} fs={74} line={86} style={{ fontFamily: 'NutriSerifText', transform: [{ scaleX: 0.946 }], transformOrigin: 'top left', letterSpacing: -0.65 }}>Healthy choices,</Txt>
    <Txt x={104} y={365} w={745} fs={74} line={86} style={{ fontFamily: 'NutriSerifText', transform: [{ scaleX: 0.973 }], transformOrigin: 'top left', letterSpacing: -0.65 }}>made simple.</Txt>
    <Txt x={109} y={473} w={704} fs={40} line={47}>{'Scan your food, get instant insights,\nand build a plan that fits your life,\nwith the power of computer vision.'}</Txt>
    <ScenePhoto scene="onboarding" />
    <Surface x={64} y={1091} w={733} h={500} radius={51} fill="#fffdf8" border={false} />
    {[
      { y: 1110, title: 'Instant food recognition', subtitle: 'Know what you’re eating', icon: 'onboarding-recognition' as const },
      { y: 1268, title: 'Personalized nutrition', subtitle: 'Get practical, realistic guidance', icon: 'onboarding-personalized' as const },
      { y: 1427, title: 'Long-term health support', subtitle: 'Small steps. Real progress.', icon: 'onboarding-support' as const },
    ].map(item => <Box key={item.title} x={38} y={38} w={786} h={1748}>
      <Surface x={86} y={item.y} w={690} h={145} radius={44} texture="onboarding-card-paper" border={false} />
      <SourceArt name={item.icon} radius={55} />
      <Txt x={238} y={item.y + 28} w={530} fs={36} bold line={43}>{item.title}</Txt>
      <Txt x={238} y={item.y + 79} w={530} fs={32} color="#575b59" line={38}>{item.subtitle}</Txt>
    </Box>)}
    {[0, 1, 2, 3].map(i => <Box key={i} x={130 + i * 39} y={1689} w={20} h={20} style={{ borderRadius: 20, backgroundColor: i === 0 ? palette.green : '#dcdcd4' }} />)}
    <SourceArt name="onboarding-continue" radius={74} />
    <Hit x={648} y={1608} w={150} h={150} label="Continue to home" onPress={home} />
  </>;
}
