import pluginVue from 'eslint-plugin-vue'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import prettierConfig from 'eslint-config-prettier'

export default [
  {
    ignores: ['node_modules', 'dist'],
  },
  ...pluginVue.configs['flat/recommended'],
  ...vueTsEslintConfig(),
  prettierConfig,
  {
    files: ['src/components/ui/*.vue'],
    rules: {
        'vue/multi-word-component-names': 'off',
    }
  }
]
