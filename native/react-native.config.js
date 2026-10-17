module.exports = {
  assets: ['./assets/fonts/'],
  // Android uses the bundled ML Kit reader. Keep the existing iOS fallback, but
  // avoid loading and packaging the unused Android ONNX runtime.
  dependencies: { 'onnxruntime-react-native': { platforms: { android: null } } },
};
