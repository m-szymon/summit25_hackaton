// Vite config for Angular frontend to allow custom hosts
import { defineConfig } from 'vite';
import angular from '@analogjs/vite-plugin-angular';

export default defineConfig({
  plugins: [angular()],
  server: {
    allowedHosts: [
      'swasik-vsearch-test-usearch.germanywestcentral.cloudapp.azure.com',
      'localhost',
      '127.0.0.1'
    ],
    host: '0.0.0.0'
  }
});
