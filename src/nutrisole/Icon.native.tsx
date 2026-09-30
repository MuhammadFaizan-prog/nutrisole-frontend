import { Camera, CalendarDays, ChartNoAxesColumnIncreasing, Footprints, UserRound, PersonStanding, ChevronRight, ChevronLeft, ArrowLeft, ArrowRight, House, NotebookText, Heart, X, Zap, Check, Scan, Minus, Plus, Info, Apple, RefreshCw, Ellipsis, MessageSquare, Flower, Accessibility, Droplet, Clock3, LockKeyhole, Activity, Settings, type LucideProps } from 'lucide-react-native';
const icons = { Camera, CalendarDays, ChartNoAxesColumnIncreasing, Footprints, UserRound, PersonStanding, ChevronRight, ChevronLeft, ArrowLeft, ArrowRight, House, NotebookText, Heart, X, Zap, Check, Scan, Minus, Plus, Info, Apple, RefreshCw, Ellipsis, MessageSquare, Flower, Accessibility, Droplet, Clock3, LockKeyhole, Activity, Settings };
import type { ComponentType } from 'react';
import type { IconName } from './iconNames';
import { SvgXml } from 'react-native-svg';
import { referenceIcons } from './referenceIcons';
export type { IconName } from './iconNames';
export default function Icon({ name, size = 40, color = '#091018', weight = 1.8, fill = 'none' }: { name: IconName; size?: number; color?: string; weight?: number; fill?: string }) {
  if (name in referenceIcons) {
    const xml = referenceIcons[name as keyof typeof referenceIcons].replaceAll('currentColor', color).replace('stroke-width="2"', `stroke-width="${weight}"`);
    return <SvgXml xml={xml} width={size} height={size} />;
  }
  const Component = icons[name as keyof typeof icons] as ComponentType<LucideProps>;
  return <Component size={size} strokeWidth={weight} color={color} fill={fill} />;
}
