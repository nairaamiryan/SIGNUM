// Checks for staged files in gesture-service/ (KAN-35). lint-staged runs them
// with gesture-service/ as the working directory. tools/run-python.mjs picks
// the project's virtual environment. Mypy and Pytest check the whole service.
const python = "node ../tools/run-python.mjs";

export default {
    "*.py": [
        `${python} -m ruff check --fix --force-exclude`,
        `${python} -m ruff format --force-exclude`,
        () => `${python} -m mypy .`,
        () => `${python} -m pytest -q`,
    ],
};
