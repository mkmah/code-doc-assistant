import tailwindcss from "@tailwindcss/vite";
import { devtools } from "@tanstack/devtools-vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { defineConfig } from "vite";
import oxlintPlugin from "vite-plugin-oxlint";
import viteTsConfigPaths from "vite-tsconfig-paths";

const config = defineConfig({
  plugins: [
    oxlintPlugin({
      configFile: ".oxlintrc.json",
    }),
    devtools(),
    nitro({
      compatibilityDate: "2025-12-24",
      vercel: {
        functions: {
          maxDuration: 300,
          runtime: "bun1.x",
        },
      },
    }),
    // this is the plugin that enables path aliases
    viteTsConfigPaths({
      projects: ["./tsconfig.json"],
    }),
    tailwindcss(),
    tanstackStart(),
    viteReact({
      // https://react.dev/learn/react-compiler
      babel: {
        plugins: [
          [
            "babel-plugin-react-compiler",
            {
              target: "19",
            },
          ],
        ],
      },
    }),
  ],
  // Fix for packages with ESM directory imports during SSR
  ssr: {
    noExternal: [/@lobehub\/.*/, /@phosphor-icons\/.*/, /@ridemountainpig\/.*/],
  },
  // Pre-bundle icon packages for faster dev server startup
  optimizeDeps: {
    include: [
      "@lobehub/icons",
      "@phosphor-icons/react",
      "lucide-react",
      "@ridemountainpig/svgl-react",
    ],
  },
});

export default config;
