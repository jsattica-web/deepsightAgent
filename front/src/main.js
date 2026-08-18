import { createApp } from 'vue'
import App from './App.vue'

// CSS는 컴포넌트와 분리하여 이곳에서 일괄 import 한다.
import './assets/styles/base.css'
import './assets/styles/icon.css'
import './assets/styles/deepsight-panel.css'
import './assets/styles/content-area.css'

createApp(App).mount('#app')
