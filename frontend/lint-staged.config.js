export default {
  "*.{ts,tsx}": ["oxlint --type-aware --fix", () => "tsgo -p ."],
  "*.{js,jsx}": ["oxlint --fix"],
};
