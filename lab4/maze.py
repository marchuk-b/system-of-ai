import random
import time

# Модель лабіринту (одиничний граф у вигляді матриці суміжності клітинок)
WALL, FREE = -1, 0          # -1 — непрохідна клітинка, 0 — прохідна

# Оператори переходу: (зміщення по рядку, зміщення по стовпцю)
CROSS = [(-1, 0), (1, 0), (0, -1), (0, 1)]        # вверх, вниз, вліво, вправо
DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]       # чотири діагоналі
OPERATORS = {
    "Вверх-вниз-вправо-вліво (4)": CROSS,
    "Діагоналі (4)": DIAG,
    "Комбінація (8)": CROSS + DIAG,
}

# Початковий лабіринт 15 x 15 ('#' — стіна, '.' — прохід)
BASE_MAZE = [
    "...#...........",
    "...#.#####.###.",
    ".#...#...#...#.",
    ".#####.#.###.#.",
    "...#...#.....#.",
    ".#.#.#########.",
    ".#...#.......#.",
    ".#####.#####.#.",
    ".....#.#...#.#.",
    "####.#.#.#.#.#.",
    "...#...#.#...#.",
    ".#.#####.#####.",
    ".#.......#.....",
    ".#########.###.",
    "...........#...",
]


class Maze:
    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.grid = [[FREE] * cols for _ in range(rows)]
        self.start = (0, 0)
        self.goal = (rows - 1, cols - 1)

    @classmethod
    def default(cls):
        m = cls(len(BASE_MAZE), len(BASE_MAZE[0]))
        for r, line in enumerate(BASE_MAZE):
            for c, ch in enumerate(line):
                m.grid[r][c] = WALL if ch == "#" else FREE
        return m

    def vid(self, cell):
        return cell[0] * self.cols + cell[1] + 1

    def resize(self, rows, cols):
        new = [[FREE] * cols for _ in range(rows)]
        for r in range(min(rows, self.rows)):
            for c in range(min(cols, self.cols)):
                new[r][c] = self.grid[r][c]
        self.rows, self.cols, self.grid = rows, cols, new
        self.start = (min(self.start[0], rows - 1), min(self.start[1], cols - 1))
        self.goal = (min(self.goal[0], rows - 1), min(self.goal[1], cols - 1))
        if self.start == self.goal:
            self.goal = (rows - 1, cols - 1) if self.start != (rows - 1, cols - 1) else (0, 0)
        self._clear_ends()

    def randomize(self, density, rng=random):
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = WALL if rng.random() < density else FREE
        self._clear_ends()

    def clear(self):
        self.grid = [[FREE] * self.cols for _ in range(self.rows)]

    def _clear_ends(self):
        for r, c in (self.start, self.goal):
            self.grid[r][c] = FREE

    def count(self):
        walls = sum(row.count(WALL) for row in self.grid)
        return self.rows * self.cols - walls, walls


# Одно-направлений хвильовий пошук (алгоритм Лі) — лишається для порівняння
def neighbors(maze, cell, moves, no_cut=False):
    r, c = cell
    g = maze.grid
    for dr, dc in moves:
        nr, nc = r + dr, c + dc
        if not (0 <= nr < maze.rows and 0 <= nc < maze.cols) or g[nr][nc] == WALL:
            continue
        # діагональний перехід «крізь кут» двох стін (за потреби забороняємо)
        if no_cut and dr and dc and (g[r + dr][c] == WALL or g[r][c + dc] == WALL):
            continue
        yield nr, nc


def wave_search(maze, moves, no_cut=False):
    s, g = maze.start, maze.goal
    t0 = time.perf_counter()
    dist = {s: 1}
    front = [s]
    waves = [[s]]              # waves[i] — вершини з міткою i+1
    per_cycle = []             # скільки вершин розкрито у кожному циклі
    cycles = expanded = 0
    found = s == g
    while front and not found:
        cycles += 1
        new, opened = [], 0
        for cell in front:
            opened += 1
            expanded += 1
            for nb in neighbors(maze, cell, moves, no_cut):
                if nb not in dist:
                    dist[nb] = dist[cell] + 1
                    new.append(nb)
                    if nb == g:
                        found = True
                        break
            if found:
                break
        per_cycle.append(opened)
        if new:
            waves.append(new)
        front = new
    # відновлення шляху зворотним ходом: від цілі до клітинки з міткою на 1 меншою
    path = []
    if found:
        cur = g
        path = [cur]
        while cur != s:
            cur = next(nb for nb in neighbors(maze, cur, moves, no_cut)
                       if dist.get(nb) == dist[cur] - 1)
            path.append(cur)
        path.reverse()
    dt = (time.perf_counter() - t0) * 1000
    return dict(found=found, path=path, cycles=cycles, expanded=expanded,
                marked=len(dist), time=dt, dist=dist, waves=waves,
                per_cycle=per_cycle)


# Двонаправлений хвильовий пошук: дві хвилі йдуть назустріч одна одній
def bidirectional_search(maze, moves, no_cut=False):
    """
    Хвиля A розповсюджується від початкової вершини, хвиля B — від цільової
    (обидві мають мітку 1 у своїй вершині). Один цикл = розкриття цілого фронту A,
    потім цілого фронту B. Пошук завершується в першому ж циклі, коли одна хвиля
    торкається клітинки, позначеної іншою хвилею; серед усіх таких зустрічей цього
    півциклу обирається найкоротша. Тоді відстань (кількість вершин шляху) =
    мітка_A(a) + мітка_B(b), де a, b — сусідні клітинки на межі двох хвиль.
    """
    s, g = maze.start, maze.goal
    t0 = time.perf_counter()
    dA, dB = {s: 1}, {g: 1}
    frA, frB = [s], [g]
    wavesA, wavesB = [[s]], [[g]]
    per_cycle = []             # (розкрито у хвилі A, розкрито у хвилі B) за цикл
    lens = [(1, 1)]            # (кількість хвиль A, B) після кожного циклу — для візуалізації
    cycles = exp_a = exp_b = 0
    best = None                # (кількість вершин шляху, a, b)
    found = s == g
    while not found and frA and frB:
        cycles += 1
        opened = [0, 0]
        for side in (0, 1):
            own, other = (dA, dB) if side == 0 else (dB, dA)
            front = frA if side == 0 else frB
            new = []
            for cell in front:
                opened[side] += 1
                for nb in neighbors(maze, cell, moves, no_cut):
                    if nb in other:                      # хвилі зустрілись
                        a, b = (cell, nb) if side == 0 else (nb, cell)
                        cost = dA[a] + dB[b]
                        if best is None or cost < best[0]:
                            best = (cost, a, b)
                    elif nb not in own:
                        own[nb] = own[cell] + 1
                        new.append(nb)
            if side == 0:
                exp_a += opened[0]
                frA = new
                if new:
                    wavesA.append(new)
            else:
                exp_b += opened[1]
                frB = new
                if new:
                    wavesB.append(new)
            if best is not None:                         # друга хвиля цього циклу вже не потрібна
                found = True
                break
        per_cycle.append(tuple(opened))
        lens.append((len(wavesA), len(wavesB)))
    # відновлення шляху: від точки зустрічі назад до початку і до цілі
    path = []
    if found:
        if s == g:
            path = [s]
        else:
            a, b = best[1], best[2]
            left, cur = [a], a
            while cur != s:
                cur = next(nb for nb in neighbors(maze, cur, moves, no_cut)
                           if dA.get(nb) == dA[cur] - 1)
                left.append(cur)
            left.reverse()
            right, cur = [b], b
            while cur != g:
                cur = next(nb for nb in neighbors(maze, cur, moves, no_cut)
                           if dB.get(nb) == dB[cur] - 1)
                right.append(cur)
            path = left + right
    dt = (time.perf_counter() - t0) * 1000
    meet = (best[1], best[2]) if best else ((s, g) if found else None)
    return dict(found=found, path=path, cycles=cycles, expanded=exp_a + exp_b,
                exp_a=exp_a, exp_b=exp_b, marked=len(dA) + len(dB), time=dt,
                dA=dA, dB=dB, wavesA=wavesA, wavesB=wavesB, per_cycle=per_cycle,
                lens=lens, meet=meet)


C = {
    "app_bg": "#1e2127",     # фон вікна / панелей
    "panel": "#262a32",      # фон карток/фреймів
    "border": "#3a3f48",     # рамки, розділювачі
    "bg": "#20232a",         # фон канви (поле лабіринту)
    "edge": "#5b636d",       # лінії сітки, другорядні контури
    "node": "#2c313a",       # прохідна клітинка
    "wall": "#0f1216",       # непрохідна клітинка (-1)
    "grid": "#3a3f48",       # сітка
    "txt": "#e7e9ec",        # текст
    "txt_dim": "#9aa3ad",    # другорядний текст
    "visited": "#2f5f85",    # клітинки, пройдені хвилею A (від старту)
    "front": "#8a6d1f",      # фронт хвилі A
    "visited_b": "#5b3f7d",  # клітинки, пройдені хвилею B (від цілі)
    "front_b": "#a1558a",    # фронт хвилі B
    "cur": "#e0803c",        # виділення
    "path": "#2fae66",       # знайдений шлях
    "acc": "#6a9bff",        # акцент (старт/ціль, кнопки)
}