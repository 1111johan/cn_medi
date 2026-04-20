import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  server: {
    host: true,
    port: 5173,
    proxy: {
      "^/(health|platform|knowledge|intake|perception|reason|research|document|smart-qa|feedback|review|governance)(/.*)?$":
        {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        clinical: resolve(__dirname, "clinical.html"),
        research: resolve(__dirname, "research.html"),
        smartQa: resolve(__dirname, "smart-qa.html"),
        rnd: resolve(__dirname, "rnd.html"),
        knowledgeCenter: resolve(__dirname, "knowledge-center.html"),
        reasoningCenter: resolve(__dirname, "reasoning-center.html"),
        expertReview: resolve(__dirname, "expert-review.html"),
        operations: resolve(__dirname, "operations.html"),
      },
    },
  },
});
