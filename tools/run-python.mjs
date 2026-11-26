import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Runs `python <args>` with the gesture-service virtual environment, so Git
// hooks work from any terminal or Git client, with or without an activated venv.
const serviceDir = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
    "gesture-service",
);
const isWindows = process.platform === "win32";
const relative = isWindows ? ["Scripts", "python.exe"] : ["bin", "python"];

const candidates = [
    path.join(serviceDir, "venv", ...relative),
    path.join(serviceDir, ".venv", ...relative),
    process.env.VIRTUAL_ENV ? path.join(process.env.VIRTUAL_ENV, ...relative) : null,
].filter(Boolean);

const python =
    candidates.find((candidate) => existsSync(candidate)) ?? (isWindows ? "python" : "python3");

const result = spawnSync(python, process.argv.slice(2), {
    stdio: "inherit",
    env: { ...process.env, PYTHONUTF8: "1" },
});

if (result.error) {
    console.error(`Could not run Python (${python}): ${result.error.message}`);
    console.error(
        "Create the virtual environment: cd gesture-service; python -m venv venv; venv\\Scripts\\activate; pip install -r requirements-dev.txt",
    );
    process.exit(1);
}
process.exit(result.status ?? 1);
