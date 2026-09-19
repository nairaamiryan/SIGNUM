# Factorial & Mathematical Calculator

A Python calculator project designed for calculating factorials ($n!$) with step-by-step mathematical breakdowns, combinatorics, and arithmetic.

---

## 🌟 Features

- **Factorial Calculation ($n!$):**
  - Iterative algorithm ($O(n)$)
  - Recursive algorithm
  - High-performance built-in (`math.factorial`)
  - Real-time step-by-step mathematical expansion (e.g. `5! = 5 × 4 × 3 × 2 × 1 = 120`)
  - Large number handling (supports arbitrarily large integers)
  - Non-integer factorials via Gamma function ($\Gamma(x+1) = x!$)
- **Combinatorics:**
  - Permutations ($^nP_r = \frac{n!}{(n-r)!}$)
  - Combinations ($^nC_r = \frac{n!}{r!(n-r)!}$)
  - Double Factorial ($n!!$)
- **Standard Arithmetic:**
  - Addition, subtraction, multiplication, division, powers
- **Interactive Interfaces:**
  - Command-line interface (CLI) with interactive menu
  - Desktop Graphical Interface (Tkinter GUI) with dark theme
  - Direct one-line command calculation

---

## 🚀 How to Run

### 1. Interactive CLI Mode
Run the calculator menu directly in your terminal:
```bash
python main.py
```

### 2. Quick One-Line Calculation
Directly calculate the factorial of any number:
```bash
python main.py 5
```
Output:
```text
Calculation Steps:
  5! = 5 × 4 × 3 × 2 × 1 = 120

Result: 5! = 120
```

### 3. Desktop GUI Mode
Launch the modern graphical calculator window:
```bash
python gui.py
# or
python main.py --gui
```

---

## 🧪 Running Unit Tests

Run the test suite to verify all mathematical operations and edge cases:
```bash
python -m unittest test_calculator.py
```

---

## 📁 Project Structure

```text
factorial.py/
├── calculator.py       # Core calculation engine & algorithms
├── main.py             # CLI runner and interactive terminal app
├── gui.py              # Tkinter desktop GUI application
├── test_calculator.py  # Unit test suite
└── README.md           # Documentation
```
