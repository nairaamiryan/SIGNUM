"""
Factorial & Arithmetic Calculator Core Engine.

This module provides the FactorialCalculator class which handles:
- Factorial computation using multiple approaches (iterative, recursive, math-optimized)
- Step-by-step mathematical expansion (e.g. 5! = 5 x 4 x 3 x 2 x 1 = 120)
- Double factorial (n!!)
- Combinations (nCr) and Permutations (nPr)
- Gamma function approximation for non-integers
- Standard arithmetic operations with calculation history
"""

import math
from typing import List, Tuple, Union, Optional


class FactorialCalculator:
    """A comprehensive calculator specialized in factorials, combinatorics, and arithmetic."""

    def __init__(self):
        self.history: List[str] = []

    def factorial_iterative(self, n: int) -> int:
        """Calculate n! iteratively."""
        self._validate_non_negative_int(n)
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

    def factorial_recursive(self, n: int) -> int:
        """Calculate n! recursively."""
        self._validate_non_negative_int(n)
        if n in (0, 1):
            return 1
        return n * self.factorial_recursive(n - 1)

    def factorial_math(self, n: int) -> int:
        """Calculate n! using Python's optimized math.factorial."""
        self._validate_non_negative_int(n)
        return math.factorial(n)

    def factorial(self, n: int, method: str = "math") -> int:
        """
        Calculate factorial of n using the selected method.
        
        Args:
            n: Non-negative integer.
            method: 'math', 'iterative', or 'recursive'.
            
        Returns:
            The factorial n! as an integer.
        """
        self._validate_non_negative_int(n)
        if method == "iterative":
            res = self.factorial_iterative(n)
        elif method == "recursive":
            res = self.factorial_recursive(n)
        else:
            res = self.factorial_math(n)

        entry = f"{n}! = {res}"
        self.history.append(entry)
        return res

    def factorial_with_steps(self, n: int) -> Tuple[int, str]:
        """
        Calculates n! and returns both the result and a step-by-step breakdown string.
        
        Example for n = 5:
            Result: 120
            Steps: "5! = 5 × 4 × 3 × 2 × 1 = 120"
        """
        self._validate_non_negative_int(n)
        result = self.factorial_math(n)

        if n == 0:
            steps = "0! = 1 (by mathematical definition)"
        elif n == 1:
            steps = "1! = 1"
        elif n <= 20:
            factors = " × ".join(str(i) for i in range(n, 0, -1))
            steps = f"{n}! = {factors} = {result}"
        else:
            factors = f"{n} × {n-1} × {n-2} × ... × 2 × 1"
            digit_count = len(str(result))
            steps = f"{n}! = {factors} = {result} ({digit_count} digits)"

        return result, steps

    def double_factorial(self, n: int) -> int:
        """
        Compute double factorial n!!:
        n!! = n * (n-2) * (n-4) * ...
        0!! = 1, (-1)!! = 1
        """
        self._validate_non_negative_int(n)
        if n in (0, 1):
            return 1
        result = 1
        for i in range(n, 0, -2):
            result *= i
        self.history.append(f"{n}!! = {result}")
        return result

    def permutations(self, n: int, r: int) -> int:
        """
        Compute permutations nPr = n! / (n - r)!
        """
        self._validate_non_negative_int(n)
        self._validate_non_negative_int(r)
        if r > n:
            raise ValueError(f"r ({r}) cannot be greater than n ({n}) for permutations.")
        res = self.factorial_math(n) // self.factorial_math(n - r)
        self.history.append(f"P({n}, {r}) = {res}")
        return res

    def combinations(self, n: int, r: int) -> int:
        """
        Compute combinations nCr = n! / (r! * (n - r)!)
        """
        self._validate_non_negative_int(n)
        self._validate_non_negative_int(r)
        if r > n:
            raise ValueError(f"r ({r}) cannot be greater than n ({n}) for combinations.")
        res = self.factorial_math(n) // (self.factorial_math(r) * self.factorial_math(n - r))
        self.history.append(f"C({n}, {r}) = {res}")
        return res

    def gamma_factorial(self, x: float) -> float:
        """
        Calculate factorial of real numbers using Gamma function: x! = Γ(x + 1).
        """
        if x < 0 and x.is_integer():
            raise ValueError("Factorial is undefined for negative integers.")
        try:
            res = math.gamma(x + 1)
            self.history.append(f"Γ({x} + 1) = {res}")
            return res
        except OverflowError:
            raise OverflowError(f"Result too large to represent for input {x}.")

    # --- Standard Arithmetic Operations ---

    def add(self, a: float, b: float) -> float:
        res = a + b
        self.history.append(f"{a} + {b} = {res}")
        return res

    def subtract(self, a: float, b: float) -> float:
        res = a - b
        self.history.append(f"{a} - {b} = {res}")
        return res

    def multiply(self, a: float, b: float) -> float:
        res = a * b
        self.history.append(f"{a} * {b} = {res}")
        return res

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        res = a / b
        self.history.append(f"{a} / {b} = {res}")
        return res

    def power(self, base: float, exponent: float) -> float:
        res = math.pow(base, exponent)
        self.history.append(f"{base} ^ {exponent} = {res}")
        return res

    def get_history(self) -> List[str]:
        """Return calculation history."""
        return list(self.history)

    def clear_history(self) -> None:
        """Clear calculation history."""
        self.history.clear()

    @staticmethod
    def _validate_non_negative_int(val: Union[int, float]) -> None:
        """Validates that input is a non-negative integer."""
        if isinstance(val, bool):
            raise TypeError("Boolean values are not valid inputs.")
        if not isinstance(val, int):
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            else:
                raise TypeError(f"Factorial requires an integer, got {type(val).__name__} ({val}).")
        if val < 0:
            raise ValueError(f"Factorial is not defined for negative integers ({val}).")
