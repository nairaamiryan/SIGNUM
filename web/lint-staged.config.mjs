// Checks for staged files in web/ (KAN-35). lint-staged runs them with web/ as
// the working directory. All commands are in one list so they run one after
// another and never edit the same file at the same time.
const config = {
    "*.{js,jsx,mjs,cjs,ts,tsx,mts,cts,json,css}": [
        "eslint --fix --no-warn-ignored",
        "prettier --write --ignore-unknown",
        () => "tsc --noEmit",
        "vitest related --run --passWithNoTests",
    ],
};

export default config;
