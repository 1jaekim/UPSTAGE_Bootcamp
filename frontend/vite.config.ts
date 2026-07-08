import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 실서버(FastAPI) 사용 시 /api → :8000 프록시. mock 모드에선 무시됨.
    // 127.0.0.1 로 고정: localhost 는 ::1(IPv6) 로 먼저 풀려 다른 리스너(예: Docker)와
    // 충돌할 수 있어 IPv4 로 직접 지정한다.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
