"""
Unit Tests for FactorialCalculator.
"""

import unittest
import math
from calculator import FactorialCalculator


class TestFactorialCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = FactorialCalculator()

    def test_factorial_base_cases(self):
        self.assertEqual(self.calc.factorial(0), 1)
        self.assertEqual(self.calc.factorial(1), 1)
        self.assertEqual(self.calc.factorial_iterative(0), 1)
        self.assertEqual(self.calc.factorial_recursive(0), 1)
        self.assertEqual(self.calc.factorial_iterative(1), 1)
        self.assertEqual(self.calc.factorial_recursive(1), 1)

    def test_factorial_standard_values(self):
        test_cases = {
            2: 2,
            3: 6,
            4: 24,
            5: 120,
            6: 720,
            7: 5040,
            10: 3628800
        }
        for n, expected in test_cases.items():
            self.assertEqual(self.calc.factorial(n, method="math"), expected)
            self.assertEqual(self.calc.factorial(n, method="iterative"), expected)
            self.assertEqual(self.calc.factorial(n, method="recursive"), expected)

    def test_steps_breakdown(self):
        res, steps = self.calc.factorial_with_steps(5)
        self.assertEqual(res, 120)
        self.assertIn("5 × 4 × 3 × 2 × 1", steps)
        self.assertIn("120", steps)

        res0, steps0 = self.calc.factorial_with_steps(0)
        self.assertEqual(res0, 1)
        self.assertIn("0! = 1", steps0)

    def test_negative_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.calc.factorial(-1)
        with self.assertRaises(ValueError):
            self.calc.factorial_iterative(-5)
        with self.assertRaises(ValueError):
            self.calc.factorial_recursive(-3)

    def test_invalid_type_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.calc.factorial(3.5)
        with self.assertRaises(TypeError):
            self.calc.factorial("5")
        with self.assertRaises(TypeError):
            self.calc.factorial(True)

    def test_double_factorial(self):
        self.assertEqual(self.calc.double_factorial(0), 1)
        self.assertEqual(self.calc.double_factorial(1), 1)
        self.assertEqual(self.calc.double_factorial(5), 15)   # 5 * 3 * 1
        self.assertEqual(self.calc.double_factorial(6), 48)   # 6 * 4 * 2

    def test_permutations(self):
        self.assertEqual(self.calc.permutations(5, 2), 20)
        self.assertEqual(self.calc.permutations(5, 5), 120)
        self.assertEqual(self.calc.permutations(5, 0), 1)
        with self.assertRaises(ValueError):
            self.calc.permutations(3, 5)

    def test_combinations(self):
        self.assertEqual(self.calc.combinations(5, 2), 10)
        self.assertEqual(self.calc.combinations(5, 5), 1)
        self.assertEqual(self.calc.combinations(5, 0), 1)
        with self.assertRaises(ValueError):
            self.calc.combinations(3, 5)

    def test_gamma_factorial(self):
        # 4! = 24
        self.assertAlmostEqual(self.calc.gamma_factorial(4.0), 24.0, places=5)
        # 0.5! = sqrt(pi)/2 ≈ 0.8862269
        self.assertAlmostEqual(self.calc.gamma_factorial(0.5), math.sqrt(math.pi) / 2, places=5)

    def test_arithmetic(self):
        self.assertEqual(self.calc.add(10, 5), 15)
        self.assertEqual(self.calc.subtract(10, 5), 5)
        self.assertEqual(self.calc.multiply(10, 5), 50)
        self.assertEqual(self.calc.divide(10, 5), 2.0)
        self.assertEqual(self.calc.power(2, 3), 8.0)
        with self.assertRaises(ZeroDivisionError):
            self.calc.divide(5, 0)

    def test_history(self):
        self.calc.clear_history()
        self.calc.factorial(4)
        self.calc.add(2, 3)
        history = self.calc.get_history()
        self.assertEqual(len(history), 2)
        self.assertIn("4! = 24", history[0])
        self.assertIn("2 + 3 = 5", history[1])


if __name__ == "__main__":
    unittest.main()
