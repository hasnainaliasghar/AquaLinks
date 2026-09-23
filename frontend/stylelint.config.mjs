/** @type {import("stylelint").Config} */
export default {
  extends: ["stylelint-config-standard"],
  rules: {
    "at-rule-no-unknown": [
      true,
      {
        ignoreAtRules: [
          "tailwind",
          "apply",
          "layer",
          "variants",
          "responsive",
          "screen",
          "config",
        ],
      },
    ],
    "no-descending-specificity": null,
    "selector-class-pattern": null,
    "custom-property-pattern": null,
    "custom-property-empty-line-before": null,
    "lightness-notation": null,
    "hue-degree-notation": null,
    "alpha-value-notation": null,
    "color-function-notation": null,
    "media-feature-range-notation": null,
    "shorthand-property-no-redundant-values": null,
    "declaration-block-no-redundant-longhand-properties": null,
    "value-keyword-case": null,
    "property-no-vendor-prefix": null,
    "declaration-block-single-line-max-declarations": null,
    "import-notation": "string",
  },
  ignoreFiles: [
    "node_modules/**/*",
    ".next/**/*",
    "out/**/*",
    "playwright-report/**/*",
    "test-results/**/*",
  ],
};
