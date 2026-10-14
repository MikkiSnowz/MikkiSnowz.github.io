import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // Lets you test on a phone on the same Wi-Fi: http://<your-computer-ip>:5173
    host: true,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
});
