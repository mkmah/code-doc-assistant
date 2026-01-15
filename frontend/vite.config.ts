import { TanStackStartRSC } from "@tanstack/start/rsc-manual"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vinxi"

export default defineConfig({
  plugins: [
    TanStackStartRSC(),
    react(),
  ],
  server: {
    port: 3000,
  },
})
