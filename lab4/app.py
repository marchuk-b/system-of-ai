import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from maze import C, OPERATORS, WALL, FREE, Maze, bidirectional_search, wave_search

SEARCH_KINDS = {
    "Однонаправлений (Лі)": "wave",
    "Двонаправлений": "bidirectional",
}


def apply_dark_theme(root):
    root.configure(bg=C["app_bg"])
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=C["panel"], foreground=C["txt"],
                    fieldbackground=C["panel"], bordercolor=C["border"],
                    darkcolor=C["panel"], lightcolor=C["panel"],
                    troughcolor=C["app_bg"], selectbackground=C["acc"],
                    selectforeground="#0b1220")

    style.configure("TFrame", background=C["panel"])
    style.configure("TLabel", background=C["panel"], foreground=C["txt"])
    style.configure("TLabelframe", background=C["panel"], foreground=C["txt"],
                    bordercolor=C["border"])
    style.configure("TLabelframe.Label", background=C["panel"], foreground=C["txt_dim"],
                    padding=(8, 0, 0, 0))

    style.configure("TButton", background=C["node"], foreground=C["txt"],
                    bordercolor=C["border"], focuscolor=C["acc"], padding=5)
    style.map("TButton",
              background=[("active", C["visited"]), ("pressed", C["visited"])],
              foreground=[("disabled", C["txt_dim"])])

    style.configure("TRadiobutton", background=C["panel"], foreground=C["txt"])
    style.map("TRadiobutton", background=[("active", C["panel"])])
    style.configure("TCheckbutton", background=C["panel"], foreground=C["txt"])
    style.map("TCheckbutton", background=[("active", C["panel"])])

    style.configure("TCombobox", background=C["node"], foreground=C["txt"],
                    fieldbackground=C["node"], arrowcolor=C["txt"],
                    selectbackground=C["node"], selectforeground=C["txt"])
    style.map("TCombobox",
              fieldbackground=[("readonly", C["node"])],
              foreground=[("readonly", C["txt"])],
              background=[("readonly", C["node"])])
    style.configure("TSpinbox", background=C["node"], foreground=C["txt"],
                    fieldbackground=C["node"], arrowcolor=C["txt"])
    style.configure("Horizontal.TScale", background=C["panel"], troughcolor=C["app_bg"])
    root.option_add("*TCombobox*Listbox.background", C["panel"])
    root.option_add("*TCombobox*Listbox.foreground", C["txt"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["acc"])

    style.configure("Vertical.TScrollbar", background=C["node"], troughcolor=C["app_bg"],
                    bordercolor=C["border"], arrowcolor=C["txt"])
    style.configure("Horizontal.TScrollbar", background=C["node"], troughcolor=C["app_bg"],
                    bordercolor=C["border"], arrowcolor=C["txt"])
    style.configure("Treeview", background=C["node"], foreground=C["txt"],
                    fieldbackground=C["node"], bordercolor=C["border"], rowheight=24)
    style.configure("Treeview.Heading", background=C["panel"], foreground=C["txt_dim"],
                    bordercolor=C["border"])
    style.map("Treeview", background=[("selected", C["visited"])])


class App:
    def __init__(self, root):
        self.root = root
        root.title("Хвильовий пошук у лабіринті")
        apply_dark_theme(root)
        self.maze = Maze.default()
        self.tool = tk.StringVar(value="sel")
        self.op = tk.StringVar(value=next(iter(OPERATORS)))
        self.search_kind = tk.StringVar(value="Двонаправлений")
        self.no_cut = tk.BooleanVar(value=False)
        self.speed = tk.IntVar(value=200)
        self.rows_v = tk.IntVar(value=self.maze.rows)
        self.cols_v = tk.IntVar(value=self.maze.cols)
        self.density = tk.DoubleVar(value=30)
        self.result = None
        self.frames, self.si, self.job = [], -1, None
        self.res_win = None
        self._last_cell = None
        self._build_ui()
        self.restore()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)  # основний вміст
        self.root.grid_rowconfigure(1, weight=0)  # журнал пошуку
        self.root.grid_columnconfigure(0, weight=1)

        content = ttk.Frame(self.root)
        content.grid(row=0, column=0, sticky="nsew")

        # Журнал
        bottom_holder = tk.Frame(self.root, height=140, bg=C["app_bg"])
        bottom_holder.grid(row=1, column=0, sticky="ew")
        bottom_holder.grid_propagate(False)
        bottom_holder.pack_propagate(False)
        bottom = ttk.LabelFrame(bottom_holder, text="Журнал пошуку", labelanchor="nw",
                                padding=(4, 4, 4, 4))
        bottom.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(bottom, orient="vertical")
        sb.pack(side="right", fill="y", pady=4)
        self.log = tk.Text(bottom, height=8, font=("Consolas", 9), wrap="word",
                           yscrollcommand=sb.set, bg=C["node"], fg=C["txt"],
                           insertbackground=C["txt"], relief="flat",
                           highlightthickness=1, highlightbackground=C["border"])
        self.log.pack(side="left", fill="both", expand=True)
        sb.config(command=self.log.yview)

        # Поле з лабіринтом та підказками
        left = ttk.Frame(content, padding=6)
        left.pack(side="left", fill="both", expand=True)
        left.grid_rowconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=0, minsize=26)
        left.grid_columnconfigure(0, weight=1)
        self.cv = tk.Canvas(left, width=960, height=620, bg=C["bg"], highlightthickness=1,
                            highlightbackground=C["border"])
        self.cv.grid(row=0, column=0, sticky="nsew")
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.cv.bind("<Button-1>", lambda e: self.click(e, False))
        self.cv.bind("<Shift-Button-1>", lambda e: self.click(e, True))
        self.cv.bind("<B1-Motion>", lambda e: self.drag(e))
        self.hint = ttk.Label(left, foreground=C["txt_dim"])
        self.hint.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Налаштування (права частина вікна)
        right = ttk.Frame(content, padding=(0, 0, 4, 0))
        right.pack(side="right", fill="y")
        panel_canvas = tk.Canvas(right, width=360, bg=C["panel"], highlightthickness=0)
        panel_scrollbar = ttk.Scrollbar(right, orient="vertical", command=panel_canvas.yview)
        panel_scrollbar.pack(side="right", fill="y")
        panel_canvas.pack(side="left", fill="both", expand=True)
        panel_canvas.configure(yscrollcommand=panel_scrollbar.set)
        p = ttk.Frame(panel_canvas, padding=8)
        panel_window = panel_canvas.create_window((0, 0), window=p, anchor="nw")
        p.bind("<Configure>", lambda event: panel_canvas.configure(
            scrollregion=panel_canvas.bbox("all")))
        panel_canvas.bind("<Configure>", lambda event: panel_canvas.itemconfigure(
            panel_window, width=event.width))

        def scroll_panel(event):
            panel_canvas.yview_scroll(-int(event.delta / 120), "units")

        def bind_panel_scroll(widget):
            widget.bind("<MouseWheel>", scroll_panel, add="+")
            for child in widget.winfo_children():
                bind_panel_scroll(child)

        # --- Параметри пошуку
        f = ttk.LabelFrame(p, text="Параметри пошуку", padding=6)
        f.pack(fill="x")
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=2)
        ttk.Label(f, text="Оператор переходу").grid(row=0, column=0, sticky="ew")
        ttk.Combobox(f, width=1, state="readonly", textvariable=self.op,
                     values=list(OPERATORS)).grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(f, text="Тип пошуку").grid(row=1, column=0, sticky="ew")
        ttk.Combobox(f, width=1, state="readonly", textvariable=self.search_kind,
                     values=list(SEARCH_KINDS)).grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Checkbutton(f, text="Не зрізати кути (діагональ між стінами)",
                        variable=self.no_cut).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Label(f, text="Початкова вершина").grid(row=3, column=0, sticky="ew")
        self.lbl_s = ttk.Label(f, foreground=C["acc"], font=("TkDefaultFont", 9, "bold"))
        self.lbl_s.grid(row=3, column=1, sticky="e")
        ttk.Label(f, text="Цільова вершина").grid(row=4, column=0, sticky="ew")
        self.lbl_g = ttk.Label(f, foreground=C["acc"], font=("TkDefaultFont", 9, "bold"))
        self.lbl_g.grid(row=4, column=1, sticky="e")
        ttk.Button(f, text="⇄  Дзеркальна заміна", command=self.swap).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.op.trace_add("write", lambda *a: self.reset())
        self.search_kind.trace_add("write", lambda *a: self.search_kind_changed())
        self.no_cut.trace_add("write", lambda *a: self.reset())

        # --- Кнопки керування
        f2 = ttk.Frame(p, padding=(0, 6))
        f2.pack(fill="x")
        for column in range(3):
            f2.columnconfigure(column, weight=1)
        f2.columnconfigure(3, weight=0)
        self.b_run = ttk.Button(f2, text="Пуск", command=self.run)
        self.b_run.grid(row=0, column=0, sticky="ew")
        ttk.Button(f2, text="Крок", command=self.step).grid(row=0, column=1, sticky="ew")
        ttk.Button(f2, text="Скинути", command=self.reset).grid(row=0, column=2, sticky="ew")
        ttk.Combobox(f2, width=6, state="readonly", textvariable=self.speed,
                     values=[600, 300, 120, 40, 0]).grid(row=0, column=3, sticky="ew")
        ttk.Label(f2, text="Затримка між циклами (мс); 0 — без анімації",
                  foreground=C["txt_dim"]).grid(row=1, column=0, columnspan=4, sticky="w")

        # --- Результати
        f3 = ttk.LabelFrame(p, text="Результати пошуку", padding=6)
        f3.pack(fill="x")
        self.out = {}
        rows = [("found", "Шлях знайдено"), ("len", "Відстань (вершин у шляху)"),
                ("cyc", "Циклів роботи"), ("exp", "Розкрито вершин"),
                ("vis", "Позначено хвилями"), ("meet", "Зустріч хвиль"),
                ("t", "Час пошуку"), ("gr", "Розмір / прохідних / стін")]
        for i, (k, name) in enumerate(rows):
            ttk.Label(f3, text=name).grid(row=i, column=0, sticky="w")
            self.out[k] = ttk.Label(f3, text="—", font=("TkDefaultFont", 9, "bold"),
                                    foreground=C["acc"])
            self.out[k].grid(row=i, column=1, sticky="e", padx=(10, 0))
        self.out["path"] = ttk.Label(f3, text="—", wraplength=310, justify="left",
                                     font=("TkDefaultFont", 9, "bold"), foreground=C["path"])
        self.out["path"].grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Button(f3, text="Відкрити вікно результатів", command=self.show_results).grid(
            row=len(rows) + 1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        # Редагування лабіринту
        f4 = ttk.LabelFrame(p, text="Редагування лабіринту", padding=6)
        f4.pack(fill="x", pady=6)
        f4.columnconfigure(0, weight=1)
        f4.columnconfigure(1, weight=1)
        tools = [("sel", "Вибір старт/ціль"), ("wall", "Стіна (-1)"), ("erase", "Прохід (0)")]
        for i, (k, name) in enumerate(tools):
            ttk.Radiobutton(f4, text=name, value=k, variable=self.tool,
                            command=self.tool_changed).grid(row=i // 2, column=i % 2, sticky="ew")

        ttk.Label(f4, text="Рядків").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(f4, text="Стовпців").grid(row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Spinbox(f4, from_=5, to=60, width=5, textvariable=self.rows_v).grid(
            row=3, column=0, sticky="ew", padx=(0, 4))
        ttk.Spinbox(f4, from_=5, to=60, width=5, textvariable=self.cols_v).grid(
            row=3, column=1, sticky="ew")
        ttk.Button(f4, text="Застосувати розмір", command=self.apply_size).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self.lbl_dens = ttk.Label(f4, text="Щільність стін: 30%")
        self.lbl_dens.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Scale(f4, from_=0, to=60, orient="horizontal", variable=self.density,
                  command=lambda v: self.lbl_dens.config(
                      text=f"Щільність стін: {int(round(float(v)))}%")).grid(
            row=6, column=0, columnspan=2, sticky="ew")
        ttk.Button(f4, text="Випадковий лабіринт", command=self.generate).grid(
            row=7, column=0, sticky="ew", pady=(4, 0), padx=(0, 4))
        ttk.Button(f4, text="Очистити", command=self.clear).grid(
            row=7, column=1, sticky="ew", pady=(4, 0))
        ttk.Button(f4, text="Відновити початковий лабіринт", command=self.restore).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Button(f4, text="Імпортувати", command=self.import_maze).grid(
            row=9, column=0, sticky="ew", pady=(4, 0), padx=(0, 4))
        ttk.Button(f4, text="Експортувати", command=self.export_maze).grid(
            row=9, column=1, sticky="ew", pady=(4, 0))
        ttk.Button(f4, text="Експортувати результат CSV", command=self.export_csv).grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        bind_panel_scroll(p)

    # Модель
    def restore(self):
        self.maze = Maze.default()
        self.rows_v.set(self.maze.rows)
        self.cols_v.set(self.maze.cols)
        self.tool_changed()
        self.reset()

    def clear(self):
        self.maze.clear()
        self.reset()

    def generate(self):
        self.maze.randomize(int(round(self.density.get())) / 100)
        self.reset()

    def apply_size(self):
        try:
            rows, cols = int(self.rows_v.get()), int(self.cols_v.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Помилка", "Розмір має бути цілим числом.")
            return
        rows, cols = max(5, min(60, rows)), max(5, min(60, cols))
        self.rows_v.set(rows)
        self.cols_v.set(cols)
        self.maze.resize(rows, cols)
        self.reset()

    def swap(self):
        m = self.maze
        m.start, m.goal = m.goal, m.start
        self.reset()

    # Керування
    def prepare(self):
        m = self.maze
        kind = SEARCH_KINDS[self.search_kind.get()]
        moves, no_cut = OPERATORS[self.op.get()], self.no_cut.get()
        if kind == "bidirectional":
            r = bidirectional_search(m, moves, no_cut)
            s_id, g_id, lens = m.vid(m.start), m.vid(m.goal), r["lens"]
            frames = [(lens[0], None,
                       f"Ініціалізація: хвиля A від №{s_id} (початок), "
                       f"хвиля B від №{g_id} (ціль)")]
            for i, (oa, ob) in enumerate(r["per_cycle"], start=1):
                na = len(r["wavesA"][lens[i][0] - 1]) if lens[i][0] > lens[i - 1][0] else 0
                nb = len(r["wavesB"][lens[i][1] - 1]) if lens[i][1] > lens[i - 1][1] else 0
                text = (f"Цикл {i}: розкрито A — {oa}, B — {ob}; "
                        f"нових клітинок A — {na}, B — {nb}")
                if r["found"] and i == len(r["per_cycle"]):
                    text += "  → хвилі зустрілись"
                frames.append((lens[i], None, text))
            final_lens = lens[-1]
            if r["found"]:
                text = (f"Шляхи з'єднано. Відстань: {len(r['path'])} вершин. Шлях: "
                        + " → ".join(str(m.vid(c)) for c in r["path"]))
            else:
                text = "Шлях не існує: одна з хвиль вичерпалась, хвилі не зустрілись"
        else:
            r = wave_search(m, moves, no_cut)
            frames = [((1, 0), None,
                       f"Ініціалізація: хвиля від №{m.vid(m.start)} (початок)")]
            for i, opened in enumerate(r["per_cycle"], start=1):
                new = len(r["waves"][i]) if i < len(r["waves"]) else 0
                frames.append(((i + 1, 0), None,
                               f"Цикл {i}: розкрито {opened} вершин(и); "
                               f"позначено {new} нових"))
            final_lens = (len(r["waves"]), 0)
            if r["found"]:
                text = "Ціль досягнута. Шлях: " + " → ".join(
                    str(m.vid(c)) for c in r["path"])
            else:
                text = "Шлях не існує: хвиля вичерпалась, ціль недосяжна"
        frames.append((final_lens, r["path"], text))
        self.result = r
        self.frames, self.si = frames, -1
        self.log.delete("1.0", "end")

        self.out["found"].config(text="так" if r["found"] else "ні")
        self.out["len"].config(text=str(len(r["path"])) if r["found"] else "—")
        self.out["cyc"].config(text=str(r["cycles"]))
        expanded = (f"{r['expanded']} ({r['exp_a']}+{r['exp_b']})"
                    if kind == "bidirectional" else str(r["expanded"]))
        self.out["exp"].config(text=expanded)
        self.out["vis"].config(text=str(r["marked"]))
        meet = r.get("meet")
        self.out["meet"].config(
            text=f"№{m.vid(meet[0])} ↔ №{m.vid(meet[1])}"
            if kind == "bidirectional" and meet else "—")
        self.out["t"].config(text=f"{r['time']:.3f} мс")
        self.out["path"].config(text=(" → ".join(str(m.vid(c)) for c in r["path"])
                                      if r["found"] else "не знайдено"))
        self.graph_info()

    def graph_info(self):
        m = self.maze
        free, walls = m.count()
        self.out["gr"].config(text=f"{m.rows}×{m.cols} / {free} / {walls}")
        self.lbl_s.config(text=f"№{m.vid(m.start)} ({m.start[0] + 1},{m.start[1] + 1})")
        self.lbl_g.config(text=f"№{m.vid(m.goal)} ({m.goal[0] + 1},{m.goal[1] + 1})")

    def tick(self):
        if self.si >= len(self.frames) - 1:
            self.stop()
            return
        self.si += 1
        self.log.insert("end", self.frames[self.si][2] + "\n")
        self.log.see("end")
        self.draw()
        if self.si >= len(self.frames) - 1:
            self.stop()
            self.show_results()
            return
        if self.job is not None:
            self.job = self.root.after(max(self.speed.get(), 1), self.tick)

    def run(self):
        if self.job is not None:
            self.stop()
            return
        if self.si >= len(self.frames) - 1 and self.si >= 0:
            self.reset()
        if self.si < 0:
            self.prepare()
        if self.speed.get() == 0:
            while self.si < len(self.frames) - 1:
                self.si += 1
                self.log.insert("end", self.frames[self.si][2] + "\n")
            self.log.see("end")
            self.draw()
            self.show_results()
            return
        self.b_run.config(text="Пауза")
        self.job = self.root.after(1, self.tick)

    def stop(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
        self.job = None
        self.b_run.config(text="Пуск")

    def step(self):
        if self.si < 0:
            self.prepare()
        self.tick()

    def reset(self, *_):
        self.stop()
        self.result = None
        self.frames, self.si = [], -1
        for k in ("found", "len", "cyc", "exp", "vis", "meet", "t", "path"):
            self.out[k].config(text="—")
        self.log.delete("1.0", "end")
        self.graph_info()
        self.draw()

    def search_kind_changed(self):
        self.reset()
        self.tool_changed()

    def tool_changed(self):
        wave_hint = ("Хвиля A: жовтий/синій, шлях — зелений."
                     if SEARCH_KINDS[self.search_kind.get()] == "wave"
                     else "Хвиля A: жовтий/синій, хвиля B: рожевий/фіолетовий, "
                     "шлях — зелений.")
        self.hint.config(text={
            "sel": "Клік по клітинці — початкова, Shift+клік — цільова.",
            "wall": "Клік/перетягування — робить клітинки непрохідними (-1).",
            "erase": "Клік/перетягування — робить клітинки прохідними (0).",
        }[self.tool.get()] + "   " + wave_hint)

    # Взаємодія
    def geom(self):
        m = self.maze
        w, h = max(self.cv.winfo_width(), 60), max(self.cv.winfo_height(), 60)
        cs = max(4, min((w - 8) // m.cols, (h - 8) // m.rows))
        return cs, (w - cs * m.cols) // 2, (h - cs * m.rows) // 2

    def cell_at(self, ev):
        cs, ox, oy = self.geom()
        r, c = (ev.y - oy) // cs, (ev.x - ox) // cs
        if 0 <= r < self.maze.rows and 0 <= c < self.maze.cols:
            return r, c
        return None

    def click(self, ev, shift):
        cell = self.cell_at(ev)
        self._last_cell = cell
        if cell is None:
            return
        m, t = self.maze, self.tool.get()
        if t == "sel":
            if shift and cell != m.start:
                m.goal = cell
            elif not shift and cell != m.goal:
                m.start = cell
            else:
                return
            m.grid[cell[0]][cell[1]] = FREE
            self.reset()
        else:
            self.paint(cell, t)

    def drag(self, ev):
        cell = self.cell_at(ev)
        if cell is None or cell == self._last_cell or self.tool.get() == "sel":
            return
        self._last_cell = cell
        self.paint(cell, self.tool.get())

    def paint(self, cell, tool):
        m = self.maze
        if cell in (m.start, m.goal):
            return
        val = WALL if tool == "wall" else FREE
        if m.grid[cell[0]][cell[1]] != val:
            m.grid[cell[0]][cell[1]] = val
            self.reset()

    # Візуалізація
    def draw(self):
        cv, m = self.cv, self.maze
        cv.delete("all")
        cs, ox, oy = self.geom()
        r = self.result
        dA = (r.get("dA", r.get("dist", {})) if r else {})
        dB = (r.get("dB", {}) if r else {})
        fr = self.frames[self.si] if self.si >= 0 else None
        ka, kb = fr[0] if fr else (0, 0)       # найбільші мітки хвиль A і B, що вже видимі
        path = set(fr[1]) if fr and fr[1] else set()
        num = cs >= 26
        font = ("TkDefaultFont", max(7, min(11, cs // 3)), "bold")

        for i in range(m.rows):
            for j in range(m.cols):
                x0, y0 = ox + j * cs, oy + i * cs
                v = m.grid[i][j]
                da, db = dA.get((i, j), 0), dB.get((i, j), 0)
                label = ""
                if v == WALL:
                    fill = C["wall"]
                    if cs >= 30:
                        label = "-1"
                else:
                    fill = C["node"]
                    if fr and 0 < da <= ka:
                        fill = C["front"] if da == ka else C["visited"]
                        label = str(da)
                    elif fr and 0 < db <= kb:
                        fill = C["front_b"] if db == kb else C["visited_b"]
                        label = str(db)
                    else:
                        label = "0"
                    if (i, j) in path:
                        fill = C["path"]
                cv.create_rectangle(x0, y0, x0 + cs, y0 + cs, fill=fill, outline=C["grid"])
                if num or (v == WALL and label):
                    color = C["txt_dim"] if v == WALL else (C["edge"] if label == "0" else C["txt"])
                    if label and (num or v == WALL):
                        cv.create_text(x0 + cs / 2, y0 + cs / 2, text=label, font=font, fill=color)

        # точка зустрічі хвиль (на останньому кадрі)
        if fr and fr[1] and r and r.get("meet"):
            for cell in set(r["meet"]):
                x0, y0 = ox + cell[1] * cs, oy + cell[0] * cs
                cv.create_rectangle(x0 + 2, y0 + 2, x0 + cs - 2, y0 + cs - 2,
                                    outline=C["cur"], width=2)

        for cell, label in ((m.start, "S"), (m.goal, "G")):
            x0, y0 = ox + cell[1] * cs, oy + cell[0] * cs
            cv.create_rectangle(x0 + 1, y0 + 1, x0 + cs - 1, y0 + cs - 1,
                                outline=C["acc"], width=3)
            if cs >= 14:
                cv.create_text(x0 + cs / 2, y0 + cs / 2, text=label, fill=C["acc"],
                               font=("TkDefaultFont", max(8, min(14, cs // 2)), "bold"))

    # Окремі вікна результатів
    def _toplevel(self, title, size):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=C["app_bg"])
        win.geometry(size)
        return win

    def show_results(self):
        r = self.result
        if r is None:
            messagebox.showinfo("Немає результату", "Спочатку запустіть пошук.")
            return
        m = self.maze
        if self.res_win is None or not self.res_win.winfo_exists():
            self.res_win = self._toplevel("Результати пошуку", "760x560")
            frm = ttk.Frame(self.res_win, padding=6)
            frm.pack(fill="both", expand=True)
            frm.grid_rowconfigure(0, weight=1)
            frm.grid_columnconfigure(0, weight=1)
            self.res_txt = tk.Text(frm, font=("Consolas", 10), wrap="none", bg=C["node"],
                                   fg=C["txt"], relief="flat", highlightthickness=1,
                                   highlightbackground=C["border"])
            vs = ttk.Scrollbar(frm, orient="vertical", command=self.res_txt.yview)
            hs = ttk.Scrollbar(frm, orient="horizontal", command=self.res_txt.xview)
            self.res_txt.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
            self.res_txt.grid(row=0, column=0, sticky="nsew")
            vs.grid(row=0, column=1, sticky="ns")
            hs.grid(row=1, column=0, sticky="ew")
        t = self.res_txt
        t.config(state="normal")
        t.delete("1.0", "end")
        free, walls = m.count()
        rc = lambda c: f"({c[0] + 1},{c[1] + 1})"       # координати: (рядок, стовпець), з 1
        L = [f"Оператор переходу : {self.op.get()}"
             + ("  (без зрізання кутів)" if self.no_cut.get() else ""),
             f"Тип пошуку        : {self.search_kind.get()}",
             f"Лабіринт          : {m.rows}×{m.cols}, прохідних {free}, стін {walls}",
             f"Початок → ціль    : №{m.vid(m.start)} {rc(m.start)} → №{m.vid(m.goal)} {rc(m.goal)}",
             f"Шлях знайдено     : {'так' if r['found'] else 'ні'}"]
        if r["found"]:
            L.append(f"Відстань          : {len(r['path'])} вершин ({len(r['path']) - 1} кроків)")
            if "meet" in r and r["meet"]:
                L.append(f"Зустріч хвиль     : №{m.vid(r['meet'][0])} {rc(r['meet'][0])} ↔ "
                         f"№{m.vid(r['meet'][1])} {rc(r['meet'][1])}")
        if "dA" in r:
            L.extend([
                f"Розкрито вершин   : {r['expanded']}  (хвиля A — {r['exp_a']}, хвиля B — {r['exp_b']})",
                f"Позначено хвилями : {r['marked']}  (A — {len(r['dA'])}, B — {len(r['dB'])})",
            ])
        else:
            L.extend([
                f"Розкрито вершин   : {r['expanded']}",
                f"Позначено хвилею  : {r['marked']}",
            ])
        L += [f"Циклів роботи     : {r['cycles']}",
              f"Час пошуку        : {r['time']:.3f} мс", ""]
        if r["found"]:
            L.append("Координати вершин найкоротшого шляху (№ (рядок,стовпець)):")
            L.append(" → ".join(f"{m.vid(c)}{rc(c)}" for c in r["path"]))
            L.append("")
        distances = ((("A — від початку", r["dA"]), ("B — від цілі", r["dB"]))
                     if "dA" in r else (("від початку", r["dist"]),))
        for name, d in distances:
            L.append(f"Матриця хвилі {name} (-1 — стіна, 0 — не досягнуто, 1 — вершина старту хвилі):")
            w = max(2, len(str(max(d.values()))) + 1)
            for i in range(m.rows):
                L.append("".join(
                    str(-1 if m.grid[i][j] == WALL else d.get((i, j), 0)).rjust(w)
                    for j in range(m.cols)))
            L.append("")
        t.insert("1.0", "\n".join(L))
        t.config(state="disabled")
        self.res_win.lift()

    def table_window(self, title, columns, rows, note="", size="900x420"):
        win = self._toplevel(title, size)
        frm = ttk.Frame(win, padding=6)
        frm.pack(fill="both", expand=True)
        tree = ttk.Treeview(frm, columns=[c for c, _, _ in columns], show="headings")
        for key, name, width in columns:
            tree.heading(key, text=name)
            tree.column(key, width=width, anchor="center")
        for row in rows:
            tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True)
        if note:
            ttk.Label(frm, text=note, foreground=C["txt_dim"], wraplength=860,
                      justify="left").pack(anchor="w", pady=(6, 0))


    # Імпорт / експорт
    def import_maze(self):
        path = filedialog.askopenfilename(
            title="Імпортувати лабіринт",
            filetypes=[("JSON-файли", "*.json"), ("Усі файли", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            grid = [[WALL if int(v) == WALL else FREE for v in row] for row in data["grid"]]
            rows, cols = len(grid), len(grid[0])
            if rows < 2 or cols < 2 or any(len(row) != cols for row in grid):
                raise ValueError("матриця має бути прямокутною (мінімум 2×2)")
            start, goal = tuple(map(int, data["start"])), tuple(map(int, data["goal"]))
            for r, c in (start, goal):
                if not (0 <= r < rows and 0 <= c < cols):
                    raise ValueError("початок або ціль поза межами матриці")
        except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Помилка імпорту", f"Не вдалося імпортувати лабіринт:\n{error}")
            return
        m = Maze(rows, cols)
        m.grid, m.start, m.goal = grid, start, goal
        m._clear_ends()
        self.maze = m
        self.rows_v.set(rows)
        self.cols_v.set(cols)
        self.reset()

    def export_maze(self):
        path = filedialog.asksaveasfilename(
            title="Експортувати лабіринт", defaultextension=".json",
            filetypes=[("JSON-файли", "*.json"), ("Усі файли", "*.*")])
        if not path:
            return
        m = self.maze
        data = {"grid": m.grid, "start": list(m.start), "goal": list(m.goal)}
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False)
        except OSError as error:
            messagebox.showerror("Помилка експорту", f"Не вдалося зберегти лабіринт:\n{error}")

    def export_csv(self):
        if self.result is None:
            messagebox.showinfo("Немає результату", "Спочатку запустіть пошук.")
            return
        path = filedialog.asksaveasfilename(
            title="Експортувати результат", defaultextension=".csv",
            filetypes=[("CSV-файли", "*.csv"), ("Усі файли", "*.*")])
        if not path:
            return
        r, m = self.result, self.maze
        free, walls = m.count()
        row = {
            "found": "так" if r["found"] else "ні",
            "path": " -> ".join(str(m.vid(c)) for c in r["path"]),
            "path_vertices": len(r["path"]) if r["found"] else "",
            "path_steps": len(r["path"]) - 1 if r["found"] else "",
            "cycles": r["cycles"],
            "expanded": r["expanded"],
            "expanded_A": r.get("exp_a", r["expanded"]),
            "expanded_B": r.get("exp_b", ""),
            "marked": r["marked"],
            "time_ms": f"{r['time']:.3f}",
            "method": SEARCH_KINDS[self.search_kind.get()],
            "operator": self.op.get(),
            "no_corner_cutting": self.no_cut.get(),
            "start": m.vid(m.start),
            "goal": m.vid(m.goal),
            "size": f"{m.rows}x{m.cols}",
            "free_cells": free,
            "walls": walls,
        }
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=row.keys())
                writer.writeheader()
                writer.writerow(row)
        except OSError as error:
            messagebox.showerror("Помилка експорту", f"Не вдалося зберегти CSV:\n{error}")