"""Мини-калькулятор: окно на tkinter с кнопками и поддержкой клавиатуры."""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

try:
    from .вычислитель import ОшибкаВыражения, вычислить, форматировать
except ImportError:  # запуск файла напрямую, без пакета
    from вычислитель import ОшибкаВыражения, вычислить, форматировать

ФОН = "#1c2230"
ЭКРАН_ФОН = "#12161f"
ТЕКСТ = "#f2f4f8"
ЦИФРА = "#2b3345"
ДЕЙСТВИЕ = "#39435c"
АКЦЕНТ = "#2f6df6"

КНОПКИ = [
    [("C", "очистить"), ("⌫", "стереть"), ("%", "ввод"), ("÷", "ввод")],
    [("7", "ввод"), ("8", "ввод"), ("9", "ввод"), ("×", "ввод")],
    [("4", "ввод"), ("5", "ввод"), ("6", "ввод"), ("−", "ввод")],
    [("1", "ввод"), ("2", "ввод"), ("3", "ввод"), ("+", "ввод")],
    [("0", "ввод"), (".", "ввод"), ("(", "ввод"), (")", "ввод")],
]


class Калькулятор(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Калькулятор")
        self.configure(bg=ФОН)
        self.resizable(False, False)

        self.выражение = tk.StringVar(value="")
        self.подсказка = tk.StringVar(value="")
        self._результат_показан = False

        self._построить_экран()
        self._построить_кнопки()
        self._настроить_клавиатуру()

    # --- интерфейс ---------------------------------------------------

    def _построить_экран(self) -> None:
        рамка = tk.Frame(self, bg=ЭКРАН_ФОН)
        рамка.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(
            рамка,
            textvariable=self.подсказка,
            font=tkfont.Font(family="Segoe UI", size=10),
            bg=ЭКРАН_ФОН,
            fg="#8b93a7",
            anchor="e",
        ).pack(fill="x", padx=12, pady=(10, 0))

        tk.Label(
            рамка,
            textvariable=self.выражение,
            font=tkfont.Font(family="Segoe UI", size=26, weight="bold"),
            bg=ЭКРАН_ФОН,
            fg=ТЕКСТ,
            anchor="e",
        ).pack(fill="x", padx=12, pady=(0, 12))

    def _построить_кнопки(self) -> None:
        сетка = tk.Frame(self, bg=ФОН)
        сетка.pack(padx=12, pady=(0, 12))

        шрифт = tkfont.Font(family="Segoe UI", size=14)

        for строка, кнопки in enumerate(КНОПКИ):
            for столбец, (подпись, роль) in enumerate(кнопки):
                цвет = ЦИФРА if подпись.isdigit() or подпись == "." else ДЕЙСТВИЕ
                tk.Button(
                    сетка,
                    text=подпись,
                    font=шрифт,
                    bg=цвет,
                    fg=ТЕКСТ,
                    activebackground=АКЦЕНТ,
                    activeforeground=ТЕКСТ,
                    relief="flat",
                    width=5,
                    height=2,
                    cursor="hand2",
                    command=lambda п=подпись, р=роль: self._нажатие(п, р),
                ).grid(row=строка, column=столбец, padx=4, pady=4)

        tk.Button(
            сетка,
            text="=",
            font=tkfont.Font(family="Segoe UI", size=14, weight="bold"),
            bg=АКЦЕНТ,
            fg=ТЕКСТ,
            activebackground="#4b82ff",
            activeforeground=ТЕКСТ,
            relief="flat",
            height=2,
            cursor="hand2",
            command=self._посчитать,
        ).grid(row=len(КНОПКИ), column=0, columnspan=4, sticky="we", padx=4, pady=(8, 4))

    def _настроить_клавиатуру(self) -> None:
        for символ in "0123456789.+-*/%()":
            self.bind(символ, lambda e: self._добавить(e.char))

        self.bind("<Return>", lambda e: self._посчитать())
        self.bind("<KP_Enter>", lambda e: self._посчитать())
        self.bind("<BackSpace>", lambda e: self._стереть())
        self.bind("<Escape>", lambda e: self._очистить())
        self.bind(",", lambda e: self._добавить("."))

    # --- логика ------------------------------------------------------

    def _нажатие(self, подпись: str, роль: str) -> None:
        if роль == "очистить":
            self._очистить()
        elif роль == "стереть":
            self._стереть()
        else:
            self._добавить(подпись)

    def _добавить(self, символ: str) -> None:
        if self._результат_показан:
            # после «=» цифра начинает новый ввод, операция продолжает вычисление
            if символ.isdigit() or символ == ".":
                self.выражение.set("")
            self._результат_показан = False
            self.подсказка.set("")

        self.выражение.set(self.выражение.get() + символ)

    def _стереть(self) -> None:
        self.подсказка.set("")
        self._результат_показан = False
        self.выражение.set(self.выражение.get()[:-1])

    def _очистить(self) -> None:
        self.выражение.set("")
        self.подсказка.set("")
        self._результат_показан = False

    def _посчитать(self) -> None:
        текст = self.выражение.get()
        if not текст.strip():
            return

        try:
            результат = вычислить(текст)
        except ОшибкаВыражения as ошибка:
            self.подсказка.set(str(ошибка))
            return

        self.подсказка.set(текст)
        self.выражение.set(форматировать(результат))
        self._результат_показан = True


def main() -> None:
    Калькулятор().mainloop()


if __name__ == "__main__":
    main()
