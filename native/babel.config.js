// G9 Stage J5 (cv-gauntlet-device): react-native-worklets requires its Babel plugin, listed LAST. VisionCamera 5 frame-processor
// worklets need it; the debug CV pipeline itself uses photo capture only. Remove this line together with the device packages.
module.exports = { presets: ['module:@react-native/babel-preset'], plugins: ['react-native-worklets/plugin'] };
