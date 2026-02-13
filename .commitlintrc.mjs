// Commitlint configuration (ES Module)
// Exported as an .mjs ESM file per your request

export default {
  extends: ["@commitlint/config-conventional"],
  // Ignore commits that include a dependabot Signed-off-by footer
  ignores: [(message) => message.includes("Signed-off-by: dependabot[bot]")],
};
