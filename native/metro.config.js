const path = require('path');
const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');
const workspaceRoot = path.resolve(__dirname, '..');
const nativePackages = ['react', 'react-native', 'react-native-svg', 'react-native-safe-area-context', 'lucide-react-native', '@react-native-async-storage/async-storage', '@react-native-documents/picker', 'onnxruntime-react-native', 'react-native-ble-plx', 'react-native-health-connect', 'react-native-image-picker'];
const defaults = getDefaultConfig(__dirname);
module.exports = mergeConfig(defaults, {
  watchFolders: [workspaceRoot],
  maxWorkers: 2,
  resolver: {
    // PP-OCRv5 models (public/ocr/ppocrv5/*.onnx) ship as raw resources in the APK.
    assetExts: [...defaults.resolver.assetExts, 'onnx'],
    nodeModulesPaths: [path.join(__dirname, 'node_modules'), path.join(workspaceRoot, 'node_modules')],
    resolveRequest: (context, moduleName, platform) => {
      const requested = nativePackages.some(name => moduleName === name || moduleName.startsWith(name + '/'))
        ? path.join(__dirname, 'node_modules', moduleName) : moduleName;
      const resolved = context.resolveRequest(context, requested, platform);
      if (resolved.type === 'sourceFile' && path.resolve(resolved.filePath) === path.join(workspaceRoot, 'src', 'nutrisole', 'primitives.native.ts')) {
        return { type: 'sourceFile', filePath: path.join(__dirname, 'touchPrimitives.tsx') };
      }
      return resolved;
    },
  },
});
