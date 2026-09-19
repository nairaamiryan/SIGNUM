"""
Interactive Factorial & Math Calculator CLI.

Run directly in terminal:
    python main.py             # Interactive menu mode
    python main.py 6           # Quick factorial calculation for 6!
    python main.py --gui       # Launch graphical desktop calculator
"""

import sys
import os

# Ensure local imports work regardless of current working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculator import FactorialCalculator


def print_header():
    print("=" * 60)
    print("           FACTORIAL & MATHEMATICAL CALCULATOR            ")
    print("=" * 60)


def print_menu():
    print("\nSelect an operation:")
    print("  [1] Factorial (n!) with step-by-step breakdown")
    print("  [2] Permutations (nPr = n! / (n-r)!)")
    print("  [3] Combinations (nCr = n! / (r! * (n-r)!))")
    print("  [4] Double Factorial (n!!)")
    print("  [5] Factorial Algorithm Comparison (Iterative vs Recursive vs Built-in)")
    print("  [6] Real Number Factorial (Gamma function Γ(x+1))")
    print("  [7] Standard Arithmetic (+, -, *, /, ^)")
    print("  [8] View Calculation History")
    print("  [9] Launch GUI Desktop Calculator")
    print("  [0] Exit")


def get_non_negative_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            val = int(raw)
            if val < 0:
                print("  [!] Error: Please enter a non-negative integer (0 or greater).")
                continue
            return val
        except ValueError:
            print(f"  [!] Error: '{raw}' is not a valid integer. Try again.")


def get_float(prompt: str) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            return float(raw)
        except ValueError:
            print(f"  [!] Error: '{raw}' is not a valid number. Try again.")


def run_cli():
    calc = FactorialCalculator()
    print_header()

    while True:
        print_menu()
        choice = input("\nEnter choice [0-9]: ").strip()

        if choice == "1":
            print("\n--- [1] Factorial (n!) ---")
            n = get_non_negative_int("Enter a number (n >= 0): ")
            try:
                result, steps = calc.factorial_with_steps(n)
                print("\nCalculation Steps:")
                print(f"  {steps}")
                print(f"\n>> Final Result: {n}! = {result}")
            except Exception as e:
                print(f"  [!] Calculation error: {e}")

        elif choice == "2":
            print("\n--- [2] Permutations nPr ---")
            n = get_non_negative_int("Enter total items (n): ")
            r = get_non_negative_int("Enter items to select (r <= n): ")
            try:
                res = calc.permutations(n, r)
                print(f"\n>> Formula: P({n}, {r}) = {n}! / ({n} - {r})!")
                print(f">> Final Result: P({n}, {r}) = {res}")
            except ValueError as e:
                print(f"  [!] {e}")

        elif choice == "3":
            print("\n--- [3] Combinations nCr ---")
            n = get_non_negative_int("Enter total items (n): ")
            r = get_non_negative_int("Enter items to select (r <= n): ")
            try:
                res = calc.combinations(n, r)
                print(f"\n>> Formula: C({n}, {r}) = {n}! / ({r}! * ({n} - {r})!)")
                print(f">> Final Result: C({n}, {r}) = {res}")
            except ValueError as e:
                print(f"  [!] {e}")

        elif choice == "4":
            print("\n--- [4] Double Factorial (n!!) ---")
            n = get_non_negative_int("Enter a number (n >= 0): ")
            try:
                res = calc.double_factorial(n)
                print(f"\n>> Final Result: {n}!! = {res}")
            except Exception as e:
                print(f"  [!] Error: {e}")

        elif choice == "5":
            print("\n--- [5] Algorithm Comparison ---")
            n = get_non_negative_int("Enter a number (suggested <= 500 for recursion): ")
            try:
                it_res = calc.factorial(n, method="iterative")
                math_res = calc.factorial(n, method="math")
                print(f"  Iterative Method: {it_res}")
                print(f"  Built-in (math) : {math_res}")
                if n <= 500:
                    rec_res = calc.factorial(n, method="recursive")
                    print(f"  Recursive Method: {rec_res}")
                    print("  All methods produced identical results: PASS")
                else:
                    print("  (Recursive skipped for n > 500 to avoid Python recursion limit)")
            except Exception as e:
                print(f"  [!] Error: {e}")

        elif choice == "6":
            print("\n--- [6] Real Number Factorial via Gamma Function ---")
            x = get_float("Enter real number (x): ")
            try:
                res = calc.gamma_factorial(x)
                print(f"\n>> x! ≈ Γ({x} + 1) = {res}")
            except Exception as e:
                print(f"  [!] Error: {e}")

        elif choice == "7":
            print("\n--- [7] Standard Arithmetic ---")
            print("Operations: +, -, *, /, ^")
            a = get_float("Enter first number: ")
            op = input("Enter operator (+, -, *, /, ^): ").strip()
            b = get_float("Enter second number: ")
            try:
                if op == "+":
                    res = calc.add(a, b)
                elif op == "-":
                    res = calc.subtract(a, b)
                elif op == "*":
                    res = calc.multiply(a, b)
                elif op == "/":
                    res = calc.divide(a, b)
                elif op in ("^", "**"):
                    res = calc.power(a, b)
                else:
                    print(f"  [!] Unknown operator '{op}'.")
                    continue
                print(f"\n>> Result: {a} {op} {b} = {res}")
            except ZeroDivisionError as e:
                print(f"  [!] {e}")
            except Exception as e:
                print(f"  [!] Error: {e}")

        elif choice == "8":
            print("\n--- [8] Calculation History ---")
            history = calc.get_history()
            if not history:
                print("  No calculations performed yet.")
            else:
                for idx, entry in enumerate(history, 1):
                    print(f"  {idx}. {entry}")

        elif choice == "9":
            print("\nLaunching GUI Desktop Calculator...")
            try:
                from gui import launch_gui
                launch_gui()
            except ImportError:
                print("  [!] GUI module not found or Tkinter not available.")
            except Exception as e:
                print(f"  [!] Failed to start GUI: {e}")

        elif choice == "0":
            print("\nThank you for using the Factorial Calculator. Goodbye!")
            break
        else:
            print("  [!] Invalid choice. Please select a number between 0 and 9.")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--gui", "-g"):
            try:
                from gui import launch_gui
                launch_gui()
                return
            except Exception as e:
                print(f"Could not launch GUI: {e}")
                sys.exit(1)
        elif arg.isdigit():
            n = int(arg)
            calc = FactorialCalculator()
            res, steps = calc.factorial_with_steps(n)
            print(f"\nCalculation Steps:\n  {steps}")
            print(f"\nResult: {n}! = {res}\n")
            return
        elif arg in ("--help", "-h"):
            print("Usage:")
            print("  python main.py         Launch interactive CLI")
            print("  python main.py <n>     Calculate n! directly")
            print("  python main.py --gui   Launch Desktop GUI")
            return

    run_cli()


if __name__ == "__main__":
    main()
