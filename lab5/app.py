import math
import csv
import json
import time
import heapq
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageEnhance, ImageOps, ImageTk

from graph import (C, BASE_XY, BASE_NAMES, BASE_E, R, Edge,
                   DEFAULT_START, DEFAULT_GOAL)

INF = float("inf")
BASE_CANVAS_WIDTH, BASE_CANVAS_HEIGHT = 960, 620
GRAPH_COLORS = {
    "edge": "#344054",
    "node": "#dbeafe",
    "text": "#111827",
    "label_bg": "#fffdf5",
    "visited": "#bfdbfe",
    "front": "#fef3c7",
    "cur": "#fed7aa",
    "path": "#15803d",
    "path_node": "#bbf7d0",
    "acc": "#7c3aed",
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

    style.configure("TCombobox", background=C["node"], foreground=C["txt"],
                    fieldbackground=C["node"], arrowcolor=C["txt"],
                    selectbackground=C["node"], selectforeground=C["txt"])
    style.map("TCombobox",
              fieldbackground=[("readonly", C["node"])],
              foreground=[("readonly", C["txt"])],
              background=[("readonly", C["node"])])
    root.option_add("*TCombobox*Listbox.background", C["panel"])
    root.option_add("*TCombobox*Listbox.foreground", C["txt"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["acc"])

    style.configure("Vertical.TScrollbar", background=C["node"], troughcolor=C["app_bg"],
                    bordercolor=C["border"], arrowcolor=C["txt"])


class App:
    def __init__(self, root):
        self.root = root
        root.title("Алгоритм Дейкстри — найкоротший шлях автошляхами України")
        apply_dark_theme(root)
        self.tool = tk.StringVar(value="sel")
        self.mode = tk.StringVar(value="graph")
        self.speed = tk.IntVar(value=200)
        self.start = tk.StringVar()
        self.goal = tk.StringVar()
        self.pick = []
        self.result = None
        self.win = None                 # вікно з результатом
        self.steps, self.si, self.job = [], -1, None
        self._build_ui()
        self.restore()

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

        # Поле з графом та підказками
        left = ttk.Frame(content, padding=6)
        left.pack(side="left", fill="both", expand=True)
        left.grid_rowconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=0, minsize=26)
        left.grid_columnconfigure(0, weight=1)
        self.cv = tk.Canvas(left, width=960, height=620, bg=C["bg"], highlightthickness=1,
                            highlightbackground=C["border"])
        self.cv.grid(row=0, column=0, sticky="nsew")
        image_path = Path(__file__).resolve().parent / "img" / "bg.jpg"
        self._bg_image = ImageEnhance.Brightness(
            Image.open(image_path).convert("RGB")
        ).enhance(1)
        self._bg_photo = None
        self.cv.bind("<Configure>", lambda _event: self.draw())
        self.cv.bind("<Button-1>", lambda e: self.click(e, False))
        self.cv.bind("<Shift-Button-1>", lambda e: self.click(e, True))
        self.hint = ttk.Label(left, text="Клік по вершині — початкова, Shift+клік — цільова.",
                              foreground=C["txt_dim"])
        self.hint.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # Налаштування (права частина вікна)
        p = ttk.Frame(content, padding=8)
        p.pack(side="right", fill="y")

        f = ttk.LabelFrame(p, text="Параметри пошуку", padding=6)
        f.pack(fill="x")
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=2)
        ttk.Label(f, text="Вид графу").grid(row=0, column=0, sticky="ew")
        ttk.Combobox(f, width=1, state="readonly", textvariable=self.mode,
                     values=["graph", "digraph"]).grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(f, text="Початкове місто").grid(row=1, column=0, sticky="ew")
        self.cb_s = ttk.Combobox(f, width=1, state="readonly", textvariable=self.start)
        self.cb_s.grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Label(f, text="Цільове місто").grid(row=2, column=0, sticky="ew")
        self.cb_g = ttk.Combobox(f, width=1, state="readonly", textvariable=self.goal)
        self.cb_g.grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Button(f, text="⇄  Дзеркальна заміна", command=self.swap).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        for var in (self.mode, self.start, self.goal):
            var.trace_add("write", lambda *a: self.reset())

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
                     values=[420, 200, 80, 0]).grid(row=0, column=3, sticky="ew")

        f3 = ttk.LabelFrame(p, text="Результати пошуку", padding=6)
        f3.pack(fill="x")
        self.out = {}
        rows = [("found", "Шлях знайдено"), ("dist", "Найкоротша відстань"),
                ("len", "Ділянок на шляху"), ("cyc", "Циклів алгоритму"),
                ("exp", "Опрацьовано вершин"), ("rel", "Релаксацій (оновлень d)"),
                ("t", "Час пошуку"), ("gr", "Порядок / розмір графу")]
        for i, (k, name) in enumerate(rows):
            ttk.Label(f3, text=name).grid(row=i, column=0, sticky="w")
            self.out[k] = ttk.Label(f3, text="—", font=("TkDefaultFont", 9, "bold"),
                                    foreground=C["acc"])
            self.out[k].grid(row=i, column=1, sticky="e", padx=(10, 0))
        self.out["path"] = ttk.Label(f3, text="—", wraplength=250, justify="left",
                                     font=("TkDefaultFont", 9, "bold"), foreground=C["path"])
        self.out["path"].grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=(6, 0))

        f4 = ttk.LabelFrame(p, text="Редагування графу", padding=6)
        f4.pack(fill="x", pady=6)
        f4.columnconfigure(0, weight=1)
        f4.columnconfigure(1, weight=1)
        tools = [("sel", "Вибір"), ("addv", "+ Вершина"), ("delv", "− Вершина"),
                 ("adde", "+ Ребро / вага"), ("dele", "− Ребро"), ("oneway", "Ребро ↔ дуга")]
        for i, (k, name) in enumerate(tools):
            ttk.Radiobutton(f4, text=name, value=k, variable=self.tool,
                            command=self.tool_changed).grid(row=i // 2, column=i % 2, sticky="ew")
        ttk.Button(f4, text="Відновити початковий граф", command=self.restore).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(f4, text="Імпортувати граф", command=self.import_graph).grid(
            row=4, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(f4, text="Експортувати граф", command=self.export_graph).grid(
            row=4, column=1, sticky="ew", pady=(4, 0))
        ttk.Button(f4, text="Експортувати результат CSV", command=self.export_csv).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    # Модель
    def restore(self):
        self.N = dict(BASE_XY)            # id -> (x, y)
        self.names = dict(BASE_NAMES)     # id -> назва міста
        self.E = [Edge(u, v, w) for u, v, w in BASE_E]
        self.start.set(DEFAULT_START)
        self.goal.set(DEFAULT_GOAL)
        self.fill_combos()
        self.reset()

    def nm(self, i):
        return self.names.get(i, str(i))

    def sid(self, name):
        """id вершини за назвою міста."""
        return next((i for i, n in self.names.items() if n == name), None)

    def fill_combos(self):
        vs = sorted(self.names.values())
        self.cb_s["values"] = vs
        self.cb_g["values"] = vs
        if self.start.get() not in vs:
            self.start.set(vs[0])
        if self.goal.get() not in vs:
            self.goal.set(vs[-1])

    def is_arc(self, e):
        return self.mode.get() == "digraph" or e.arc

    def adj(self, u):
        """Суміжні вершини з вагами ребер: [(v, w), ...]."""
        res = []
        for e in self.E:
            if e.u == u and e.v in self.N:
                res.append((e.v, e.w))
            elif e.v == u and not self.is_arc(e) and e.u in self.N:
                res.append((e.u, e.w))
        res.sort(key=lambda t: (t[1], self.nm(t[0])))
        return res

    def find_edge(self, a, b, exact=False):
        for k, e in enumerate(self.E):
            if (e.u == a and e.v == b) if exact else {e.u, e.v} == {a, b}:
                return k
        return None

    # Алгоритм Дейкстри
    def dijkstra(self, s, g):
        t0 = time.perf_counter()
        nm = self.nm
        dist, parent, done = {s: 0}, {}, set()
        pq = [(0, s)]                      # черга з пріоритетом (мінімальна d зверху)
        steps, cycles, relax, found = [], 0, 0, False

        def snap(cur, path, text):
            front = {v for v in dist if v not in done}
            steps.append((front, set(done), cur, path, text, dict(dist)))

        snap(None, None, f"Ініціалізація: d({nm(s)}) = 0, для решти d = ∞")
        while pq:
            d, u = heapq.heappop(pq)
            if u in done:                   # застарілий запис у черзі
                continue
            cycles += 1
            done.add(u)
            snap(u, None, f"Цикл {cycles}: обрано {nm(u)} з мінімальною d = {d} км — відстань остаточна")
            if u == g:
                found = True
                break
            for v, w in self.adj(u):
                if v in done:
                    continue
                nd = d + w
                old = dist.get(v, INF)
                if nd < old:
                    dist[v], parent[v] = nd, u
                    heapq.heappush(pq, (nd, v))
                    relax += 1
                    snap(u, None, f"   релаксація {nm(u)}→{nm(v)} ({w}): d({nm(v)}) = {nd}"
                                  f" (було {'∞' if old == INF else old})")
                else:
                    snap(u, None, f"   {nm(u)}→{nm(v)} ({w}): {nd} ≥ {old} — без змін")
        dt = (time.perf_counter() - t0) * 1000
        path = []
        if found:
            x = g
            while x is not None:
                path.append(x)
                x = parent.get(x)
            path.reverse()
        total = dist.get(g) if found else None
        snap(g if found else None, path,
             (f"Ціль досягнута. Шлях: {' → '.join(map(nm, path))}; відстань {total} км")
             if found else "Шлях не існує: ціль недосяжна")
        return dict(steps=steps, found=found, path=path, dist=total, cycles=cycles,
                    expanded=len(done), relax=relax, time=dt)

    # Керування
    def prepare(self):
        r = self.dijkstra(self.sid(self.start.get()), self.sid(self.goal.get()))
        self.result = r
        self.steps, self.si = r["steps"], -1
        self.log.delete("1.0", "end")
        self.out["found"].config(text="так" if r["found"] else "ні")
        self.out["dist"].config(text=f"{r['dist']} км" if r["found"] else "—")
        self.out["len"].config(text=str(len(r["path"]) - 1) if r["found"] else "—")
        self.out["cyc"].config(text=str(r["cycles"]))
        self.out["exp"].config(text=str(r["expanded"]))
        self.out["rel"].config(text=str(r["relax"]))
        self.out["t"].config(text=f"{r['time']:.3f} мс")
        self.out["path"].config(text=" → ".join(map(self.nm, r["path"])) if r["found"]
                                else "не знайдено")
        self.graph_info()

    def graph_info(self):
        self.out["gr"].config(text=f"{len(self.N)} / {len(self.E)}")

    def show_result(self):
        """Окреме вікно з найкоротшим шляхом (перелік міст) та віддаллю."""
        r = self.result
        if r is None:
            return
        if self.win is not None and self.win.winfo_exists():
            self.win.destroy()
        w = tk.Toplevel(self.root)
        self.win = w
        w.title("Найкоротший шлях")
        w.configure(bg=C["app_bg"])
        w.transient(self.root)
        w.resizable(False, True)
        frame = ttk.Frame(w, padding=12)
        frame.pack(fill="both", expand=True)
        s, g = self.start.get(), self.goal.get()
        ttk.Label(frame, text=f"{s} → {g}", font=("TkDefaultFont", 12, "bold"),
                  foreground=C["acc"]).pack(anchor="w")
        if not r["found"]:
            ttk.Label(frame, text="Шлях не існує: цільове місто недосяжне\n"
                                  "за поточним набором доріг.",
                      foreground=C["cur"], justify="left").pack(anchor="w", pady=8)
        else:
            txt = tk.Text(frame, width=46, height=min(len(r["path"]) + 1, 20),
                          font=("Consolas", 10), bg=C["node"], fg=C["txt"], relief="flat",
                          highlightthickness=1, highlightbackground=C["border"])
            txt.pack(fill="both", expand=True, pady=8)
            txt.tag_config("tot", foreground=C["path"], font=("Consolas", 10, "bold"))
            acc = 0
            for k, v in enumerate(r["path"]):
                if k == 0:
                    txt.insert("end", f"{k + 1:>2}. {self.nm(v)}\n")
                    continue
                u = r["path"][k - 1]
                leg = min((e.w for e in self.E
                           if (e.u == u and e.v == v)
                           or (e.u == v and e.v == u and not self.is_arc(e))), default=0)
                acc += leg
                txt.insert("end", f"{k + 1:>2}. {self.nm(v):<18} +{leg:>4} км  (всього {acc})\n")
            txt.insert("end", f"\nЗагальна відстань: {r['dist']} км", "tot")
            txt.config(state="disabled")
            ttk.Label(frame, text=f"Міст на шляху: {len(r['path'])}, ділянок: {len(r['path']) - 1}",
                      foreground=C["txt_dim"]).pack(anchor="w")
        ttk.Button(frame, text="Закрити", command=w.destroy).pack(anchor="e", pady=(8, 0))

    def import_graph(self):
        path = filedialog.askopenfilename(
            title="Імпортувати граф",
            filetypes=[("JSON-файли", "*.json"), ("Усі файли", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            nodes, edges = data["nodes"], data["edges"]
            xy = {int(i): (int(n["x"]), int(n["y"])) for i, n in nodes.items()}
            names = {int(i): str(n["name"]) for i, n in nodes.items()}
            imported_edges = [Edge(int(e["u"]), int(e["v"]), int(e["w"]),
                                   bool(e.get("arc", False))) for e in edges]
            if not xy:
                raise ValueError("граф не містить вершин")
            if len(set(names.values())) != len(names):
                raise ValueError("назви міст мають бути унікальними")
            if any(e.u not in xy or e.v not in xy for e in imported_edges):
                raise ValueError("ребро посилається на відсутню вершину")
            if any(e.w <= 0 for e in imported_edges):
                raise ValueError("ваги ребер мають бути додатними")
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Помилка імпорту", f"Не вдалося імпортувати граф:\n{error}")
            return

        self.N, self.names, self.E = xy, names, imported_edges
        self.fill_combos()
        self.reset()

    def export_graph(self):
        path = filedialog.asksaveasfilename(
            title="Експортувати граф",
            defaultextension=".json",
            filetypes=[("JSON-файли", "*.json"), ("Усі файли", "*.*")],
        )
        if not path:
            return
        data = {
            "nodes": {str(i): {"name": self.names[i], "x": x, "y": y}
                      for i, (x, y) in self.N.items()},
            "edges": [{"u": e.u, "v": e.v, "w": e.w, "arc": e.arc} for e in self.E],
        }
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
        except OSError as error:
            messagebox.showerror("Помилка експорту", f"Не вдалося зберегти граф:\n{error}")

    def export_csv(self):
        if self.result is None:
            messagebox.showinfo("Немає результату", "Спочатку запустіть пошук.")
            return
        path = filedialog.asksaveasfilename(
            title="Експортувати результат",
            defaultextension=".csv",
            filetypes=[("CSV-файли", "*.csv"), ("Усі файли", "*.*")],
        )
        if not path:
            return
        r = self.result
        row = {
            "found": "так" if r["found"] else "ні",
            "path": " -> ".join(map(self.nm, r["path"])),
            "distance_km": r["dist"] if r["found"] else "",
            "path_edges": len(r["path"]) - 1 if r["found"] else "",
            "cycles": r["cycles"],
            "expanded": r["expanded"],
            "relaxations": r["relax"],
            "time_ms": f"{r['time']:.3f}",
            "graph_type": self.mode.get(),
            "start": self.start.get(),
            "goal": self.goal.get(),
            "vertices": len(self.N),
            "edges": len(self.E),
        }
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=row.keys())
                writer.writeheader()
                writer.writerow(row)
        except OSError as error:
            messagebox.showerror("Помилка експорту", f"Не вдалося зберегти CSV:\n{error}")

    def tick(self):
        if self.si >= len(self.steps) - 1:
            self.stop()
            return
        self.si += 1
        self.log.insert("end", self.steps[self.si][4] + "\n")
        self.log.see("end")
        self.draw()
        if self.si >= len(self.steps) - 1:   # останній крок — показати результат
            self.stop()
            self.show_result()
            return
        if self.job is not None:
            self.job = self.root.after(max(self.speed.get(), 1), self.tick)

    def run(self):
        if self.job is not None:
            self.stop()
            return
        if self.si < 0:
            self.prepare()
        if self.speed.get() == 0:
            while self.si < len(self.steps) - 1:
                self.si += 1
                self.log.insert("end", self.steps[self.si][4] + "\n")
            self.log.see("end")
            self.draw()
            self.show_result()
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
        self.steps, self.si, self.pick = [], -1, []
        for k in ("found", "dist", "len", "cyc", "exp", "rel", "t", "path"):
            self.out[k].config(text="—")
        self.log.delete("1.0", "end")
        self.graph_info()
        self.draw()

    def swap(self):
        s, g = self.start.get(), self.goal.get()
        self.start.set(g)
        self.goal.set(s)
        self.reset()

    def tool_changed(self):
        self.pick = []
        self.hint.config(text={
            "sel": "Клік по вершині — початкова, Shift+клік — цільова.",
            "addv": "Клік по вільному місцю — додати нове місто (запитає назву).",
            "delv": "Клік по вершині — видалити її та всі інцидентні ребра.",
            "adde": "Клік по двох містах — додати ребро (запитає відстань) або змінити вагу існуючого.",
            "dele": "Клік по двох містах — видалити ребро/дугу між ними.",
            "oneway": "Клік по двох містах — зробити ребро дугою a→b і навпаки.",
        }[self.tool.get()])
        self.draw()

    # Взаємодія
    def click(self, ev, shift):
        x, y = self._to_graph(self.cv.canvasx(ev.x), self.cv.canvasy(ev.y))
        hit = next((i for i, (nx, ny) in self.N.items() if math.hypot(nx - x, ny - y) < R + 4), None)
        t = self.tool.get()
        if t == "addv":
            if hit is None:
                name = simpledialog.askstring("Нова вершина", "Назва міста:", parent=self.root)
                if name is None:
                    return
                name = name.strip()
                if not name or self.sid(name) is not None:
                    messagebox.showwarning("Некоректна назва",
                                           "Назва має бути непорожньою та унікальною.")
                    return
                nid = max(self.N, default=0) + 1
                self.N[nid] = (int(x), int(y))
                self.names[nid] = name
                self.fill_combos()
                self.reset()
            return
        if hit is None:
            return
        if t == "sel":
            (self.goal if shift else self.start).set(self.nm(hit))
            return
        if t == "delv":
            if len(self.N) <= 2:
                messagebox.showinfo("Граф", "У графі має лишитися щонайменше дві вершини.")
                return
            self.N.pop(hit, None)
            self.names.pop(hit, None)
            self.E = [e for e in self.E if e.u != hit and e.v != hit]
            self.fill_combos()
            self.reset()
            return
        self.pick.append(hit)
        if len(self.pick) == 2:
            a, b = self.pick
            self.pick = []
            if a != b:
                digraph = self.mode.get() == "digraph"
                if t == "adde":
                    i = self.find_edge(a, b, exact=digraph)
                    old = self.E[i].w if i is not None else 1
                    w = simpledialog.askinteger(
                        "Вага ребра", f"Відстань {self.nm(a)} — {self.nm(b)}, км:",
                        parent=self.root, initialvalue=old, minvalue=1, maxvalue=100000)
                    if w is not None:
                        if i is None:
                            self.E.append(Edge(a, b, w))
                        else:
                            self.E[i].w = w
                elif t == "dele":
                    i = self.find_edge(a, b, exact=digraph)
                    if i is not None:
                        self.E.pop(i)
                elif t == "oneway":
                    i = self.find_edge(a, b)
                    if i is not None:
                        self.E[i].arc = not self.E[i].arc
                        self.E[i].u, self.E[i].v = a, b
            self.reset()
        else:
            self.draw()

    # Візуалізація
    def _canvas_transform(self):
        scale = min(self.cv.winfo_width() / BASE_CANVAS_WIDTH,
                    self.cv.winfo_height() / BASE_CANVAS_HEIGHT)
        offset_x = (self.cv.winfo_width() - BASE_CANVAS_WIDTH * scale) / 2
        offset_y = (self.cv.winfo_height() - BASE_CANVAS_HEIGHT * scale) / 2
        return scale, offset_x, offset_y

    def _to_canvas(self, x, y):
        scale, offset_x, offset_y = self._canvas_transform()
        return offset_x + x * scale, offset_y + y * scale

    def _to_graph(self, x, y):
        scale, offset_x, offset_y = self._canvas_transform()
        return (x - offset_x) / scale, (y - offset_y) / scale

    def _draw_background(self):
        width, height = self.cv.winfo_width(), self.cv.winfo_height()
        if width <= 1 or height <= 1:
            return
        background = ImageOps.fit(
            self._bg_image, (width, height), method=Image.Resampling.LANCZOS
        )
        self._bg_photo = ImageTk.PhotoImage(background)
        self.cv.delete("bg-image")
        self.cv.create_image(0, 0, image=self._bg_photo, anchor="nw", tags="bg-image")
        self.cv.tag_lower("bg-image")

    def draw(self):
        cv = self.cv
        cv.delete("all")
        self._draw_background()
        scale, _, _ = self._canvas_transform()
        st = self.steps[self.si] if self.si >= 0 else None
        q = st[0] if st else set()
        done = st[1] if st else set()
        cur = st[2] if st else None
        path = st[3] if st and st[3] else []
        dist = st[5] if st else {}
        pe = {frozenset(p) for p in zip(path, path[1:])}
        s, g = self.sid(self.start.get()), self.sid(self.goal.get())
        pairs = {(e.u, e.v) for e in self.E}

        labels = []
        for e in self.E:
            if e.u not in self.N or e.v not in self.N:
                continue
            x1, y1 = self._to_canvas(*self.N[e.u])
            x2, y2 = self._to_canvas(*self.N[e.v])
            arc = self.is_arc(e)
            L = math.hypot(x2 - x1, y2 - y1) or 1
            if arc and (e.v, e.u) in pairs:      # протилежні дуги — зсув убік
                ox, oy = -(y2 - y1) / L * 5 * scale, (x2 - x1) / L * 5 * scale
                x1, y1, x2, y2 = x1 + ox, y1 + oy, x2 + ox, y2 + oy
            on = frozenset((e.u, e.v)) in pe
            col = GRAPH_COLORS["path"] if on else GRAPH_COLORS["edge"]
            cv.create_line(x1, y1, x2, y2, fill=col, width=(4 if on else 2) * scale)
            if arc:
                a = math.atan2(y2 - y1, x2 - x1)
                hx, hy = x2 - math.cos(a) * R * scale, y2 - math.sin(a) * R * scale
                cv.create_polygon(hx, hy,
                                  hx - 12 * scale * math.cos(a - .4),
                                  hy - 12 * scale * math.sin(a - .4),
                                  hx - 12 * scale * math.cos(a + .4),
                                  hy - 12 * scale * math.sin(a + .4),
                                  fill=col)
            labels.append(((x1 + x2) / 2, (y1 + y2) / 2, e.w, on))

        for x, y, w, on in labels:               # ваги ребер
            t = cv.create_text(x, y, text=str(w), font=("TkDefaultFont", 7),
                               fill="#166534" if on else GRAPH_COLORS["text"])
            bx = cv.bbox(t)
            r = cv.create_rectangle(bx[0] - 1, bx[1] - 1, bx[2] + 1, bx[3] + 1,
                                    fill=GRAPH_COLORS["label_bg"], outline="")
            cv.tag_lower(r, t)

        for i, (graph_x, graph_y) in self.N.items():
            x, y = self._to_canvas(graph_x, graph_y)
            fill = GRAPH_COLORS["node"]
            if i in done:
                fill = GRAPH_COLORS["visited"]
            if i in q:
                fill = GRAPH_COLORS["front"]
            if i in path:
                fill = GRAPH_COLORS["path_node"]
            if i == cur:
                fill = GRAPH_COLORS["cur"]
            outline, w = GRAPH_COLORS["edge"], 2
            if i in (s, g):
                outline, w = GRAPH_COLORS["acc"], 3
            if i in self.pick:
                outline, w = "#c2410c", 3
            radius = R * scale
            cv.create_oval(x - radius, y - radius, x + radius, y + radius,
                           fill=fill, outline=outline, width=w * scale)
            self._draw_canvas_label(
                x, y + radius + 8 * scale, self.nm(i),
                font=("TkDefaultFont", max(1, round(8 * scale)), "bold"),
                fill=GRAPH_COLORS["text"],
            )
            if i in dist:                        # поточна відстань d(v) від старту
                self._draw_canvas_label(
                    x, y - radius - 7 * scale, str(dist[i]),
                    font=("TkDefaultFont", max(1, round(8 * scale)), "bold"),
                    fill="#c2410c" if i == cur else GRAPH_COLORS["acc"],
                )
            if i in (s, g):
                self._draw_canvas_label(
                    x, y - radius - (19 if i in dist else 8) * scale,
                    "СТАРТ" if i == s else "ЦІЛЬ",
                    font=("TkDefaultFont", max(1, round(7 * scale)), "bold"),
                    fill=GRAPH_COLORS["acc"],
                )

    def _draw_canvas_label(self, x, y, text, *, font, fill):
        label = self.cv.create_text(x, y, text=text, font=font, fill=fill)
        bounds = self.cv.bbox(label)
        if bounds:
            background = self.cv.create_rectangle(
                bounds[0] - 2, bounds[1] - 1, bounds[2] + 2, bounds[3] + 1,
                fill=GRAPH_COLORS["label_bg"], outline="",
            )
            self.cv.tag_lower(background, label)