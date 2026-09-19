"""
Graphical User Interface (GUI) for Factorial & Math Calculator.

Built with Python's standard Tkinter library.
Provides a modern dark-themed calculator interface with direct buttons for:
- Factorial (n!)
- Double Factorial (n!!)
- Permutations (nPr) and Combinations (nCr)
- Step-by-step breakdown modal/panel
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calculator import FactorialCalculator


class CalculatorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Factorial & Math Calculator")
        self.root.geometry("420x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.calc = FactorialCalculator()
        self.current_expr = ""
        self.steps_text = ""

        self._setup_styles()
        self._create_widgets()
        self._bind_keys()

    def _setup_styles(self):
        self.colors = {
            "bg": "#1e1e2e",
            "screen_bg": "#181825",
            "screen_fg": "#cdd6f4",
            "subtext": "#a6adc8",
            "btn_num": "#313244",
            "btn_num_hover": "#45475a",
            "btn_op": "#89b4fa",
            "btn_op_fg": "#11111b",
            "btn_fact": "#f38ba8",
            "btn_fact_fg": "#11111b",
            "btn_action": "#a6e3a1",
            "btn_action_fg": "#11111b",
            "btn_clear": "#eba0ac",
            "btn_clear_fg": "#11111b",
            "border": "#45475a"
        }

    def _create_widgets(self):
        # Display frame
        display_frame = tk.Frame(self.root, bg=self.colors["screen_bg"], padx=15, pady=12)
        display_frame.pack(fill="x", padx=15, pady=(15, 10))

        # Secondary display for steps or status
        self.sub_display = tk.Label(
            display_frame,
            text="Ready | Enter an integer and press n!",
            font=("Consolas", 10),
            bg=self.colors["screen_bg"],
            fg=self.colors["subtext"],
            anchor="e"
        )
        self.sub_display.pack(fill="x")

        # Main expression display
        self.main_display = tk.Entry(
            display_frame,
            font=("Consolas", 24, "bold"),
            bg=self.colors["screen_bg"],
            fg=self.colors["screen_fg"],
            bd=0,
            justify="right",
            insertbackground="#cdd6f4"
        )
        self.main_display.pack(fill="x", pady=(5, 0))
        self.main_display.insert(0, "0")

        # Step breakdown view frame
        self.step_frame = tk.Frame(self.root, bg="#24273a", padx=10, pady=6)
        self.step_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.step_label = tk.Label(
            self.step_frame,
            text="Steps: (Calculations will show here)",
            font=("Segoe UI", 9, "italic"),
            bg="#24273a",
            fg="#bac2de",
            anchor="w",
            wraplength=380,
            justify="left"
        )
        self.step_label.pack(fill="x")

        # Buttons grid
        grid_frame = tk.Frame(self.root, bg=self.colors["bg"])
        grid_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Define button layout
        buttons = [
            [("C", self._on_clear, "clear"), ("⌫", self._on_backspace, "clear"), ("x!", self._on_factorial, "fact"), ("x!!", self._on_double_fact, "fact")],
            [("nPr", self._on_npr, "fact"), ("nCr", self._on_ncr, "fact"), ("^", lambda: self._append_op("**"), "op"), ("/", lambda: self._append_op("/"), "op")],
            [("7", lambda: self._append_num("7"), "num"), ("8", lambda: self._append_num("8"), "num"), ("9", lambda: self._append_num("9"), "num"), ("*", lambda: self._append_op("*"), "op")],
            [("4", lambda: self._append_num("4"), "num"), ("5", lambda: self._append_num("5"), "num"), ("6", lambda: self._append_num("6"), "num"), ("-", lambda: self._append_op("-"), "op")],
            [("1", lambda: self._append_num("1"), "num"), ("2", lambda: self._append_num("2"), "num"), ("3", lambda: self._append_num("3"), "num"), ("+", lambda: self._append_op("+"), "op")],
            [("0", lambda: self._append_num("0"), "num"), (".", lambda: self._append_num("."), "num"), ("Steps", self._show_detailed_steps, "fact"), ("=", self._on_equal, "action")]
        ]

        for r_idx, row in enumerate(buttons):
            grid_frame.rowconfigure(r_idx, weight=1)
            for c_idx, (text, cmd, b_type) in enumerate(row):
                grid_frame.columnconfigure(c_idx, weight=1)
                btn = self._make_button(grid_frame, text, cmd, b_type)
                btn.grid(row=r_idx, column=c_idx, padx=4, pady=4, sticky="nsew")

    def _make_button(self, parent, text, command, b_type):
        bg = self.colors["btn_num"]
        fg = self.colors["screen_fg"]

        if b_type == "op":
            bg = self.colors["btn_op"]
            fg = self.colors["btn_op_fg"]
        elif b_type == "fact":
            bg = self.colors["btn_fact"]
            fg = self.colors["btn_fact_fg"]
        elif b_type == "action":
            bg = self.colors["btn_action"]
            fg = self.colors["btn_action_fg"]
        elif b_type == "clear":
            bg = self.colors["btn_clear"]
            fg = self.colors["btn_clear_fg"]

        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 12, "bold"),
            bg=bg,
            fg=fg,
            activebackground="#585b70",
            activeforeground="#ffffff",
            bd=0,
            relief="flat",
            command=command,
            cursor="hand2"
        )
        return btn

    def _bind_keys(self):
        self.root.bind("<Return>", lambda e: self._on_equal())
        self.root.bind("<BackSpace>", lambda e: self._on_backspace())
        self.root.bind("<Escape>", lambda e: self._on_clear())

    def _get_display_val(self) -> str:
        return self.main_display.get().strip()

    def _set_display_val(self, val: str):
        self.main_display.delete(0, tk.END)
        self.main_display.insert(0, str(val))

    def _append_num(self, char: str):
        current = self._get_display_val()
        if current == "0" and char != ".":
            self._set_display_val(char)
        else:
            self.main_display.insert(tk.END, char)

    def _append_op(self, op: str):
        current = self._get_display_val()
        if current:
            self.main_display.insert(tk.END, f" {op} ")

    def _on_clear(self):
        self._set_display_val("0")
        self.sub_display.config(text="Cleared")
        self.step_label.config(text="Steps: Cleared")

    def _on_backspace(self):
        current = self._get_display_val()
        if len(current) > 1:
            self._set_display_val(current[:-1].rstrip())
        else:
            self._set_display_val("0")

    def _on_factorial(self):
        raw = self._get_display_val()
        try:
            val = int(raw)
            if val < 0:
                messagebox.showerror("Error", "Factorial is not defined for negative numbers.")
                return
            if val > 1500:
                confirm = messagebox.askyesno("Warning", f"Calculating {val}! may take a moment. Proceed?")
                if not confirm:
                    return

            res, steps = self.calc.factorial_with_steps(val)
            self.steps_text = steps
            self.sub_display.config(text=f"{val}! calculated")
            self.step_label.config(text=f"Steps: {steps}")
            self._set_display_val(str(res))
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter an integer for factorial.")

    def _on_double_fact(self):
        raw = self._get_display_val()
        try:
            val = int(raw)
            if val < 0:
                messagebox.showerror("Error", "Double factorial is not defined for negative numbers.")
                return
            res = self.calc.double_factorial(val)
            self.sub_display.config(text=f"{val}!! calculated")
            self.step_label.config(text=f"Steps: {val}!! = {res}")
            self._set_display_val(str(res))
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter an integer for double factorial.")

    def _on_npr(self):
        self._prompt_two_param("nPr (Permutations)", self.calc.permutations, "P")

    def _on_ncr(self):
        self._prompt_two_param("nCr (Combinations)", self.calc.combinations, "C")

    def _prompt_two_param(self, title, func, symbol):
        current = self._get_display_val()
        try:
            n_default = int(current) if current.isdigit() else 5
        except ValueError:
            n_default = 5

        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("280x180")
        dialog.configure(bg="#181825")
        dialog.resizable(False, False)

        tk.Label(dialog, text=f"Calculate {title}:", font=("Segoe UI", 10, "bold"), bg="#181825", fg="#cdd6f4").pack(pady=10)

        f1 = tk.Frame(dialog, bg="#181825")
        f1.pack(pady=2)
        tk.Label(f1, text="Total items (n):", width=14, anchor="w", bg="#181825", fg="#a6adc8").pack(side="left")
        e_n = tk.Entry(f1, width=8)
        e_n.insert(0, str(n_default))
        e_n.pack(side="left")

        f2 = tk.Frame(dialog, bg="#181825")
        f2.pack(pady=4)
        tk.Label(f2, text="Selected (r):", width=14, anchor="w", bg="#181825", fg="#a6adc8").pack(side="left")
        e_r = tk.Entry(f2, width=8)
        e_r.insert(0, "2")
        e_r.pack(side="left")

        def compute():
            try:
                n = int(e_n.get().strip())
                r = int(e_r.get().strip())
                res = func(n, r)
                self.sub_display.config(text=f"{symbol}({n}, {r})")
                self.step_label.config(text=f"Result: {symbol}({n}, {r}) = {res}")
                self._set_display_val(str(res))
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dialog)

        tk.Button(dialog, text="Calculate", bg="#89b4fa", fg="#11111b", command=compute).pack(pady=12)

    def _on_equal(self):
        expr = self._get_display_val()
        try:
            # Safe evaluation for standard math expressions
            allowed_chars = set("0123456789+-*/. ()eE")
            cleaned_expr = expr.replace("**", "^")
            # Replace ^ with ** for python eval
            python_expr = expr.replace("^", "**")
            if not all(c in allowed_chars or c in "^ " for c in expr):
                raise ValueError("Expression contains unsupported characters.")

            res = eval(python_expr, {"__builtins__": None}, {})
            if isinstance(res, float) and res.is_integer():
                res = int(res)

            self.sub_display.config(text=f"{expr} =")
            self.step_label.config(text=f"Steps: {expr} = {res}")
            self._set_display_val(str(res))
        except ZeroDivisionError:
            messagebox.showerror("Error", "Cannot divide by zero.")
        except Exception:
            messagebox.showerror("Error", "Invalid expression.")

    def _show_detailed_steps(self):
        if not self.steps_text:
            messagebox.showinfo("Steps Breakdown", "Calculate a factorial (n!) first to see full steps.")
            return

        detail_win = tk.Toplevel(self.root)
        detail_win.title("Step-by-Step Breakdown")
        detail_win.geometry("450x250")
        detail_win.configure(bg="#181825")

        tk.Label(
            detail_win,
            text="Factorial Mathematical Breakdown",
            font=("Segoe UI", 12, "bold"),
            bg="#181825",
            fg="#cdd6f4"
        ).pack(pady=10)

        t = tk.Text(detail_win, wrap="word", bg="#1e1e2e", fg="#cdd6f4", font=("Consolas", 10), padx=10, pady=10)
        t.insert("1.0", self.steps_text)
        t.config(state="disabled")
        t.pack(fill="both", expand=True, padx=10, pady=(0, 10))


def launch_gui():
    root = tk.Tk()
    app = CalculatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
