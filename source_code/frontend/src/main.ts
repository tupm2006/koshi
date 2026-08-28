import { createApp } from 'vue';
import { createPinia } from 'pinia';
import './app.css';
import App from './App.vue';
import { useThemeStore } from './stores/themeStore';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

// Initialize theme store before mount
const themeStore = useThemeStore(pinia);
themeStore.init();

app.mount('#app');
