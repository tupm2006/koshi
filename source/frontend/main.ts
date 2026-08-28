import { createApp } from 'vue';
import { createPinia } from 'pinia';
import './app.css';
import App from './App.vue';
import { useThemeStore } from './stores/themeStore';
import { useI18nStore } from './stores/i18nStore';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

// Initialize theme store before mount
const themeStore = useThemeStore(pinia);
themeStore.init();

// Locale before mount, so the first paint is already in the right language.
useI18nStore(pinia).init();

app.mount('#app');
