import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig, loadEnv } from "vite"
import { inspectAttr } from 'kimi-plugin-inspect-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiPort = env.VITE_API_PORT || '8001'

  return {
    plugins: [inspectAttr(), react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      allowedHosts: true,
      // 백엔드 포트: 기본 8001 (uvicorn --port 8001). 8000 사용 시 .env에 VITE_API_PORT=8000
      proxy: {
        '/api': {
          target: `http://127.0.0.1:${apiPort}`,
          changeOrigin: true,
          secure: false,
        },
        '/health': {
          target: `http://127.0.0.1:${apiPort}`,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})
