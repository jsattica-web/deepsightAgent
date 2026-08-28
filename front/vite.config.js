import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 프론트엔드는 로컬/컨테이너 모두 8088을 사용한다.
const FRONT_PORT = 8088

// 프록시 대상은 agent-python(FastAPI)이다. 로컬 기본 포트는 8000이다.
const AGENT_ORIGIN = 'http://localhost:8000'

// 운영의 nginx 프록시와 동일한 규칙을 개발 서버에도 적용한다.
// 덕분에 코드에서는 환경과 무관하게 '/api/...' 상대경로만 쓰면 된다.
//
// agent-python은 '/api' 프리픽스 없이 '/agent/chat', '/tools/...' 로 서빙하므로
// nginx와 똑같이 프리픽스를 떼고 넘긴다. (예: /api/agent/chat -> /agent/chat)
const proxy = {
  '/api': {
    target: AGENT_ORIGIN,
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '')
  }
}

export default defineConfig({
  plugins: [vue()],
  server: {
    // 기본값('localhost')은 Node 17+ 에서 IPv6 루프백(::1)에만 바인딩되어
    // http://127.0.0.1:8088 접속이 실패한다. 명시적으로 IPv4에 바인딩한다.
    // LAN의 다른 기기(휴대폰 등)에서 접속하려면 true 또는 '0.0.0.0'으로 바꾼다.
    host: '127.0.0.1',
    port: FRONT_PORT,
    // 포트가 사용 중이면 조용히 다른 포트로 넘어가지 않고 실패시킨다.
    strictPort: true,
    proxy
  },
  preview: {
    host: '127.0.0.1',
    port: FRONT_PORT,
    strictPort: true,
    proxy
  }
})
