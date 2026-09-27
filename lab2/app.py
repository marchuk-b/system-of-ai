import math
import csv
import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import deque

from graph import C, BASE_XY, BASE_E, R, Edge

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
        root.title("Пошук у графі: DFS / BFS")
        apply_dark_theme(root)
        self.tool = tk.StringVar(value="sel")
        self.mode = tk.StringVar(value="graph")
        self.algorithm = tk.StringVar(value="dfs")
        self.order = tk.StringVar(value="asc")
        self.speed = tk.IntVar(value=200)
        self.start = tk.IntVar(value=1)
        self.goal = tk.IntVar(value=19)
        self.pick = []
        self.result = None
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
        self.cv.bind("<Button-1>", lambda e: self.click(e, False))
        self.cv.bind("<Shift-Button-1>", lambda e: self.click(e, True))
        self.hint = ttk.Label(left, text="Клік по вершині — початкова, Shift+клік — цільова.",
                             foreground=C["txt_dim"])
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

        f = ttk.LabelFrame(p, text="Параметри пошуку", padding=6)
        f.pack(fill="x")
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=2)
        ttk.Label(f, text="Метод пошуку").grid(row=0, column=0, sticky="ew")
        ttk.Combobox(f, width=1, state="readonly", textvariable=self.algorithm,
                 values=["dfs", "bfs"]).grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(f, text="Вид графу").grid(row=1, column=0, sticky="ew")
        ttk.Combobox(f, width=1, state="readonly", textvariable=self.mode,
                 values=["graph", "digraph", "tree"]).grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Label(f, text="Порядок обходу").grid(row=2, column=0, sticky="ew")
        ttk.Combobox(f, width=1, state="readonly", textvariable=self.order,
                 values=["asc", "desc"]).grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Label(f, text="Початкова вершина").grid(row=3, column=0, sticky="ew")
        self.cb_s = ttk.Combobox(f, width=1, state="readonly", textvariable=self.start)
        self.cb_s.grid(row=3, column=1, sticky="ew", pady=2)
        ttk.Label(f, text="Цільова вершина").grid(row=4, column=0, sticky="ew")
        self.cb_g = ttk.Combobox(f, width=1, state="readonly", textvariable=self.goal)
        self.cb_g.grid(row=4, column=1, sticky="ew", pady=2)
        ttk.Button(f, text="⇄  Дзеркальна заміна", command=self.swap).grid(row=5, column=0, columnspan=2,
                                                                          sticky="ew", pady=(4, 0))
        for var in (self.algorithm, self.mode, self.order, self.start, self.goal):
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
        rows = [("found", "Шлях знайдено"), ("len", "Довжина шляху (ребер)"),
                ("cyc", "Циклів алгоритму"), ("exp", "Розкрито вершин"),
                ("vis", "Згенеровано (відвідано)"), ("t", "Час пошуку"),
                ("gr", "Порядок / розмір графу")]
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
                 ("adde", "± Ребро/дуга"), ("oneway", "Ребро ↔ дуга")]
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
        bind_panel_scroll(p)

    # Модель
    def restore(self):
        self.N = dict(BASE_XY)
        self.E = [Edge(u, v, bool(t)) for u, v, t in BASE_E]
        self.fill_combos()
        self.start.set(1)
        self.goal.set(19)
        self.reset()

    def fill_combos(self):
        vs = sorted(self.N)
        self.cb_s["values"] = vs
        self.cb_g["values"] = vs
        if self.start.get() not in self.N:
            self.start.set(vs[0])
        if self.goal.get() not in self.N:
            self.goal.set(vs[-1])

    def live(self, e):
        return e.tree if self.mode.get() == "tree" else True

    def is_arc(self, e):
        return self.mode.get() == "digraph" or e.arc

    def adj(self, u):
        """Суміжні вершини у заданому порядку обходу."""
        res = []
        for e in self.E:
            if not self.live(e):
                continue
            if e.u == u:
                res.append(e.v)
            elif e.v == u and not self.is_arc(e):
                res.append(e.u)
        res = [v for v in dict.fromkeys(res) if v in self.N]
        o = self.order.get()
        if o == "asc":
            res.sort()
        elif o == "desc":
            res.sort(reverse=True)
        return res

    # Пошук у ширину та глибину використовують спільний формат кроків для візуалізації.
    def search(self, s, g, algorithm="dfs"):
        t0 = time.perf_counter()
        frontier = deque([s]) if algorithm == "bfs" else [(s, None)]
        frontier_name = "черга" if algorithm == "bfs" else "стек"
        visited, expanded_nodes, parent = {s}, set(), {}
        steps, cycles, expanded, found = [], 0, 0, False
        steps.append(([s], set(visited), None, None,
                      f"Ініціалізація: {frontier_name} = [{s}]"))
        while frontier:
            cycles += 1
            if algorithm == "bfs":
                u = frontier.popleft()
            else:
                u, predecessor = frontier.pop()
                if u in expanded_nodes:
                    steps.append(([node for node, _ in frontier], set(visited), u, None,
                                  f"Цикл {cycles}: вершину {u} вже відвідано"))
                    continue
                visited.add(u)
                if predecessor is not None:
                    parent[u] = predecessor
            expanded_nodes.add(u)
            expanded += 1
            pending = list(frontier) if algorithm == "bfs" else [node for node, _ in frontier]
            steps.append((pending, set(visited), u, None,
                          f"Цикл {cycles}: розкрито вершину {u}"))
            if u == g:
                found = True
                break
            neighbors = self.adj(u)
            if algorithm == "dfs":
                neighbors.reverse()
            for v in neighbors:
                if algorithm == "bfs" and v not in visited:
                    visited.add(v)
                    parent[v] = u
                    frontier.append(v)
                    pending = list(frontier)
                    steps.append((pending, set(visited), u, None,
                                  f"   генерація {v} (з {u}); {frontier_name} = {pending}"))
                elif algorithm == "dfs" and v not in expanded_nodes:
                    visited.add(v)
                    frontier.append((v, u))
                    pending = [node for node, _ in frontier]
                    steps.append((pending, set(visited), u, None,
                                  f"   генерація {v} (з {u}); {frontier_name} = {pending}"))
        dt = (time.perf_counter() - t0) * 1000
        path = []
        if found:
            x = g
            while x is not None:
                path.append(x)
                x = parent.get(x)
            path.reverse()
        pending = list(frontier) if algorithm == "bfs" else [node for node, _ in frontier]
        steps.append((pending, set(visited), g if found else None, path,
                      ("Ціль досягнута. Шлях: " + " → ".join(map(str, path))) if found
                      else "Шлях не існує: ціль недосяжна"))
        return dict(steps=steps, found=found, path=path, cycles=cycles,
                    expanded=expanded, visited=len(visited), time=dt)

    def bfs(self, s, g):
        return self.search(s, g, "bfs")

    def dfs(self, s, g):
        return self.search(s, g, "dfs")

    # Керування
    def prepare(self):
        search = self.bfs if self.algorithm.get() == "bfs" else self.dfs
        r = search(self.start.get(), self.goal.get())
        self.result = r
        self.steps, self.si = r["steps"], -1
        self.log.delete("1.0", "end")
        self.out["found"].config(text="так" if r["found"] else "ні")
        self.out["len"].config(text=str(len(r["path"]) - 1) if r["found"] else "—")
        self.out["cyc"].config(text=str(r["cycles"]))
        self.out["exp"].config(text=str(r["expanded"]))
        self.out["vis"].config(text=str(r["visited"]))
        self.out["t"].config(text=f"{r['time']:.3f} мс")
        self.out["path"].config(text=" → ".join(map(str, r["path"])) if r["found"] else "не знайдено")
        self.graph_info()

    def graph_info(self):
        self.out["gr"].config(text=f"{len(self.N)} / {sum(1 for e in self.E if self.live(e))}")

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
            nodes = data["nodes"]
            edges = data["edges"]
            imported_nodes = {int(node_id): (int(position[0]), int(position[1]))
                              for node_id, position in nodes.items()}
            imported_edges = [Edge(int(edge["u"]), int(edge["v"]),
                                   bool(edge.get("tree", False)),
                                   bool(edge.get("arc", False)))
                              for edge in edges]
            if not imported_nodes:
                raise ValueError("граф не містить вершин")
            if any(edge.u not in imported_nodes or edge.v not in imported_nodes
                   for edge in imported_edges):
                raise ValueError("ребро посилається на відсутню вершину")
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Помилка імпорту", f"Не вдалося імпортувати граф:\n{error}")
            return

        self.N, self.E = imported_nodes, imported_edges
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
            "nodes": {str(node_id): list(position) for node_id, position in self.N.items()},
            "edges": [{"u": edge.u, "v": edge.v, "tree": edge.tree, "arc": edge.arc}
                      for edge in self.E],
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
        result = self.result
        row = {
            "found": "так" if result["found"] else "ні",
            "path": " -> ".join(map(str, result["path"])),
            "path_length": len(result["path"]) - 1 if result["found"] else "",
            "cycles": result["cycles"],
            "expanded": result["expanded"],
            "visited": result["visited"],
            "time_ms": f"{result['time']:.3f}",
            "graph_type": self.mode.get(),
            "search_method": self.algorithm.get(),
            "order": self.order.get(),
            "start": self.start.get(),
            "goal": self.goal.get(),
            "vertices": len(self.N),
            "edges": sum(1 for edge in self.E if self.live(edge)),
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
        for k in ("found", "len", "cyc", "exp", "vis", "t", "path"):
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
            "addv": "Клік по вільному місцю — додати нову вершину.",
            "delv": "Клік по вершині — видалити її та всі інцидентні зв'язки.",
            "adde": "Клік по двох вершинах — додати/видалити зв'язок (в оргграфі — розворот дуги).",
            "oneway": "Клік по двох вершинах — зробити ребро дугою u→v і навпаки.",
        }[self.tool.get()])
        self.draw()

    # Взаємодія
    def click(self, ev, shift):
        x, y = self.cv.canvasx(ev.x), self.cv.canvasy(ev.y)
        hit = next((i for i, (nx, ny) in self.N.items() if math.hypot(nx - x, ny - y) < R + 4), None)
        t = self.tool.get()
        if t == "addv":
            if hit is None:
                nid = max(self.N) + 1
                self.N[nid] = (int(x), int(y))
                self.fill_combos()
                self.reset()
            return
        if hit is None:
            return
        if t == "sel":
            (self.goal if shift else self.start).set(hit)
            return
        if t == "delv":
            self.N.pop(hit, None)
            self.E = [e for e in self.E if e.u != hit and e.v != hit]
            self.fill_combos()
            self.reset()
            return
        self.pick.append(hit)
        if len(self.pick) == 2:
            a, b = self.pick
            self.pick = []
            if a != b:
                i = next((k for k, e in enumerate(self.E)
                          if {e.u, e.v} == {a, b}), None)
                if t == "adde":
                    if i is None:
                        self.E.append(Edge(a, b))
                    elif self.mode.get() == "digraph" and self.E[i].u == b:
                        self.E[i].u, self.E[i].v = a, b      # розворот дуги
                    else:
                        self.E.pop(i)
                elif t == "oneway" and i is not None:
                    self.E[i].arc = not self.E[i].arc
                    self.E[i].u, self.E[i].v = a, b
            self.reset()
        else:
            self.draw()

    # Візуалізація
    def draw(self):
        cv = self.cv
        cv.delete("all")
        st = self.steps[self.si] if self.si >= 0 else None
        q = set(st[0]) if st else set()
        vis = st[1] if st else set()
        cur = st[2] if st else None
        path = st[3] if st and st[3] else []
        pe = {frozenset(p) for p in zip(path, path[1:])}
        s, g = self.start.get(), self.goal.get()

        for e in self.E:
            if not self.live(e) or e.u not in self.N or e.v not in self.N:
                continue
            (x1, y1), (x2, y2) = self.N[e.u], self.N[e.v]
            on = frozenset((e.u, e.v)) in pe
            cv.create_line(x1, y1, x2, y2, fill=C["path"] if on else C["edge"],
                           width=4 if on else 2)
            if self.is_arc(e):
                a = math.atan2(y2 - y1, x2 - x1)
                hx, hy = x2 - math.cos(a) * R, y2 - math.sin(a) * R
                cv.create_polygon(hx, hy,
                                  hx - 12 * math.cos(a - .4), hy - 12 * math.sin(a - .4),
                                  hx - 12 * math.cos(a + .4), hy - 12 * math.sin(a + .4),
                                  fill=C["path"] if on else C["edge"])

        for i, (x, y) in self.N.items():
            fill = C["node"]
            if i in vis:
                fill = C["visited"]
            if i in q:
                fill = C["front"]
            if i in path:
                fill = C["path"]
            if i == cur:
                fill = C["cur"]
            outline, w = C["edge"], 2
            if i in (s, g):
                outline, w = C["acc"], 4
            if i in self.pick:
                outline, w = C["cur"], 4
            cv.create_oval(x - R, y - R, x + R, y + R, fill=fill, outline=outline, width=w)
            cv.create_text(x, y, text=str(i), font=("TkDefaultFont", 9, "bold"), fill=C["txt"])
            if i in (s, g):
                cv.create_text(x, y - R - 10, text="СТАРТ" if i == s else "ЦІЛЬ",
                               font=("TkDefaultFont", 8, "bold"), fill=C["acc"])