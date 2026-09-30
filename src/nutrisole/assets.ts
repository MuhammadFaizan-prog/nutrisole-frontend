import { sourceArt } from './sourceArt';
import { surfaceAssets } from './surfaceAssets';
export const assets = Object.fromEntries([
  'apple-thumbnail', 'apple-thumbnail-home', 'berry-oats', 'chicken-quinoa-bowl', 'chicken-bowl-home',
  'alex-avatar', 'alex-avatar-home', 'onboarding-hero', 'leaf-brand-mark', 'gallery-thumbnail',
  'warm-background-tile', 'dark-green-texture-tile', 'dark-green-scan-texture-tile', 'pale-green-texture-tile',
  'lavender-texture-tile', 'pale-green-estimate-texture-tile', 'gray-track-texture-tile', 'warm-card-texture-tile',
  'home-progress-ring', 'weekly-progress-ring', 'scan-backdrop-clean', 'scan-photo-region', 'onboarding-photo-region', 'scan-time-background', 'scan-indicators-background',
  ...Object.values(sourceArt).map(art => art.asset),
  ...surfaceAssets,
].map(name => [name, { uri: `/nutrisole/${name}.png` }])) as Record<string, { uri: string }>;
