import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '/usr/build/dist',
    emptyOutDir: true,
  },
  server: {
    fs: {
      cachedChecks: false
    },
    proxy: {
      '/api': {
        target: 'http://nginx:80',
        changeOrigin: true
      }
    }
  }
})
