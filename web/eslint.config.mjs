import next from "eslint-config-next";

const config = [
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
  ...next,
  {
    rules: {
      // French copy uses apostrophes everywhere; escaping them hurts readability.
      "react/no-unescaped-entities": "off",
      // Data fetching legitimately updates state from an effect.
      "react-hooks/set-state-in-effect": "off",
    },
  },
];

export default config;
