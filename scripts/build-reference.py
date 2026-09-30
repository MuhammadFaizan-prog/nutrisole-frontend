"""Attach implementation calibration to the full original reference transcription."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
reference = json.loads((root.parent / 'NutriSole-UI-Reference.json').read_text(encoding='utf-8-sig'))
reference['implementation'] = {
    'date': '2026-09-30',
    'appDirectory': str(root),
    'previewUrl': 'http://localhost:4173/',
    'stack': {'shared': 'React Native + TypeScript', 'preview': 'React Native Web + Vite + protected Product Design mobile runtime', 'native': 'Expo SDK 57 + Expo Router'},
    'sourcePixelDisplayCropsXYWH': {
        'onboarding': [38, 38, 786, 1748], 'home': [42, 38, 777, 1737], 'scan': [41, 37, 781, 1739],
        'log-meal': [55, 120, 750, 1604], 'weekly-plan': [57, 149, 749, 1537], 'profile': [50, 166, 760, 1564],
    },
    'transform': 'Uniform min(viewportWidth/cropWidth, viewportHeight/cropHeight); top aligned; horizontally centered. Source coordinates are translated by crop origin.',
    'previewDeviceViewports': {'iPhone': [393, 852], 'Pixel10': [427, 952]},
    'calibrationAuthority': 'src/nutrisole/ui.tsx and individual screen components. Earlier bounding-box estimates elsewhere in this JSON remain advisory.',
    'fonts': {'sans': 'Roboto 400/600', 'serif': 'Libre Caslon Display 400', 'onboardingSerif': 'Libre Caslon Text 400, calibrated size/tracking and horizontal scale', 'boldSerif': 'Libre Caslon Text 700, horizontal scale 0.82', 'sourceIdentityVerified': False},
    'icons': {'referenceArtwork': '44 individual unlabeled source icon/badge/button PNG crops inside semantic controls', 'secondaryStates': 'Lucide and pinned Tabler 3.48.0 library assets', 'originalVectorsAvailable': False},
    'assetProvenance': ['assets/source/provenance.json', 'assets/source/scenes.provenance.json', 'assets/source/icon-art.provenance.json', 'assets/source/surfaces.provenance.json', 'assets/icons/provenance.json', 'artifacts/figma/photograph-provenance.json'],
    'photoRendering': 'ScenePhoto masks all source UI pixels before displaying camera/onboarding photo regions. Never render those region assets directly. Generated recovery only fills unavailable photograph behind excluded controls.',
    'persistence': {'key': 'nutrisole.demo.v1', 'web': 'localStorage', 'native': 'AsyncStorage', 'data': 'Synthetic fixtures and local edits only'},
    'verification': {'domainTests': 5, 'runtimeProtectedFiles': 28, 'rootTypecheck': 'passed', 'webBuild': 'passed', 'nativeTypecheck': 'passed', 'nativeLint': 'passed', 'nativeExports': ['ios', 'android'], 'nativeDeviceTested': False, 'browserFlowEvidence': 'Prior iteration passed; artifacts/qa/browser-final-checks.json', 'latestBrowserVisualCheck': 'blocked by automatic browser review; no workaround used', 'visualGate': 'blocked: unverified original fonts, reconstructed surface/photo lighting, and final captures unavailable'},
    'evidenceDirectory': 'artifacts/qa/exact-refinement',
    'captureFreshness': 'Full-page comparisons precede the last onboarding paper/headline and camera-mask/pointer refinements; they do not prove the latest state.',
    'figma': {'url': 'https://www.figma.com/design/UQU8ormOKktMlOTzsZaRko', 'fileKey': 'UQU8ormOKktMlOTzsZaRko', 'mainFrames': 6, 'frameSize': [393, 852], 'components': 79, 'mainFrameLiveTextNodes': 132, 'prototypeNavigationLinks': 16, 'sceneSpecification': 'artifacts/figma/scenes.json', 'ledger': 'artifacts/figma/design-system-state.json', 'editable': 'Live text, surfaces, source asset instances, vectors, and semantic action layers; no whole-screen UI raster', 'finalVisualCheck': 'pending: Starter MCP call limit; native activation recovery failed', 'temporaryQACompositionId': '2:2'},
    'qaReport': 'design-qa.md',
    'buildPrompt': 'UI_BUILD_PROMPT.md',
}
(root / 'UI-Reference.json').write_text(json.dumps(reference, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('Saved the full reference transcription with current implementation calibration.')
