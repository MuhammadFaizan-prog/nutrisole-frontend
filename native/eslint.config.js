const { defineConfig, globalIgnores } = require('eslint/config');
const { createRequire } = require('module');
const expoConfig = require('eslint-config-expo/flat');
const expoRequire = createRequire(require.resolve('eslint-config-expo/flat'));
const parserPath = expoRequire.resolve('@typescript-eslint/parser');
module.exports = defineConfig([
  globalIgnores(['dist-check/**', '.expo/**']),
  expoConfig,
  {
    // Imported shared screens live above native/; resolve the nested parser explicitly.
    settings: { 'import/parsers': { '@typescript-eslint/parser': [], [parserPath]: ['.ts', '.tsx', '.d.ts'] } },
  },
]);
