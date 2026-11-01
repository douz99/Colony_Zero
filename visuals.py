"""Original vector building symbols drawn with Tk; no image assets required."""


def draw_facility(canvas, kind, x, y, scale=1.0, level=1):
    """Draw around (x,y) inside a roughly 46 by 30 logical-pixel box."""
    def rectangle(a, b, c, d, **options):
        return canvas.create_rectangle(x + a * scale, y + b * scale,
                                       x + c * scale, y + d * scale, **options)

    def line(*points, **options):
        coords = [offset + value * scale for index, value in enumerate(points)
                  for offset in [x if index % 2 == 0 else y]]
        return canvas.create_line(*coords, **options)

    if kind == "solar":
        line(-12, 14, -8, 2, 9, 2, 13, 14, fill="#a3b8c9", width=2)
        rectangle(-23, -13, 23, 3, fill="#224f79", outline="#e6b655", width=2)
        for a in (-11, 0, 11):
            line(a, -12, a, 2, fill="#8bc8ec")
        line(-22, -5, 22, -5, fill="#8bc8ec")
        if level == 2:
            rectangle(-18, 7, 18, 16, fill="#224f79", outline="#e6b655")
            for a in (-9, 0, 9):
                line(a, 7, a, 16, fill="#8bc8ec")
    elif kind == "farm":
        canvas.create_arc(x - 24 * scale, y - 23 * scale, x + 24 * scale, y + 23 * scale,
                          start=0, extent=180, fill="#336d61", outline="#72c99b", width=2)
        rectangle(-24, 0, 24, 12, fill="#254d46", outline="#72c99b")
        for a in (-13, 0, 13):
            line(a, 9, a, -6, fill="#c0ee9c", width=2)
            line(a, 3, a - 5, -1, fill="#8bdd8b", width=2)
        if level == 2:
            rectangle(15, -7, 30, 12, fill="#336d61", outline="#a7e8af", width=2)
            line(22, 9, 22, -3, fill="#c0ee9c", width=2)
    elif kind == "mine":
        rectangle(-22, -4, 9, 13, fill="#594974", outline="#b49ddb", width=2)
        rectangle(-13, -17, -5, -4, fill="#8d78b0", outline="")
        line(11, 13, 11, -17, 23, -17, 23, -5, fill="#ccb8eb", width=3)
        canvas.create_polygon(x + 19 * scale, y - 5 * scale, x + 27 * scale, y - 5 * scale,
                              x + 23 * scale, y + 2 * scale, fill="#e6b655")
        rectangle(-17, 4, -9, 11, fill="#1c283c", outline="")
        if level == 2:
            rectangle(-27, 5, -17, 14, fill="#8d78b0", outline="#ccb8eb")
            line(-25, -8, -25, 2, -19, 2, fill="#ccb8eb", width=2)
    elif kind in ("home", "hq"):
        color = "#73d9cf" if kind == "hq" else "#7cbcea"
        rectangle(-21, -6, 21, 14, fill="#2d5368", outline=color, width=2)
        canvas.create_polygon(x - 24 * scale, y - 6 * scale, x, y - 20 * scale,
                              x + 24 * scale, y - 6 * scale, fill=color)
        rectangle(-5, 2, 5, 14, fill="#142436", outline="")
        for a in (-15, 11):
            rectangle(a, 0, a + 5, 5, fill="#e5d9a2", outline="")
        if kind == "hq":
            line(0, -20, 0, -28, 12, -28, fill=color, width=2)
        elif level == 2:
            rectangle(21, -3, 33, 14, fill="#2d5368", outline=color, width=2)
            rectangle(25, 1, 29, 6, fill="#ffdc91", outline="")


def draw_board(canvas, game, selected, palette, planned_kind=None, translator=str, font_family="Segoe UI"):
    """Map labels remain legible without relying on colour alone."""
    from engine import BUILDINGS, SIZE

    canvas.delete("all")
    width = max(1, canvas.winfo_width())
    height = max(1, canvas.winfo_height())
    cell_w, cell_h = width / SIZE, height / SIZE
    offline = set(game.forecast()["offline_tiles"]) if game.status == "active" else set()
    selected_kind = game.grid[selected[0]][selected[1]] or planned_kind
    neighbours = set(game.neighbors(*selected))
    for r in range(SIZE):
        for c in range(SIZE):
            kind = game.grid[r][c]
            level = game.levels[r][c]
            x1, y1 = c * cell_w + 3, r * cell_h + 3
            x2, y2 = (c + 1) * cell_w - 3, (r + 1) * cell_h - 3
            color = BUILDINGS.get(kind, {}).get("color", palette["muted"])
            outline = palette["accent"] if selected == (r, c) else "#365069"
            if (r, c) in neighbours:
                pair = {selected_kind, kind}
                if pair == {"farm", "home"}:
                    outline = "#72c99b"
                elif pair == {"mine", "home"}:
                    outline = "#f0a07c"
            canvas.create_rectangle(x1, y1, x2, y2, fill="#243c4f" if kind else "#142b3b",
                                    outline=outline, width=3 if selected == (r, c) else 1)
            if not kind:
                # Sparse deterministic terrain texture, no asset or random state.
                for dot in range(3):
                    dx = (r * 17 + c * 11 + dot * 23) % max(1, int(cell_w - 16))
                    dy = (c * 13 + r * 7 + dot * 19) % max(1, int(cell_h - 14))
                    canvas.create_oval(x1+7+dx, y1+6+dy, x1+9+dx, y1+8+dy, fill="#294355", outline="")
            canvas.create_text(x1 + 7, y1 + 5, text=f"{chr(65 + r)}{c + 1}", anchor="nw",
                               fill=palette["muted"], font=(font_family, 8))
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            if kind:
                # Reserve a caption band even in the minimum-height window.
                scale = min(cell_w / 85, max(0.18, (cell_h - 20) / 65), 1.1)
                draw_facility(canvas, kind, cx, cy - 7, scale, level)
                if level:
                    canvas.create_text(x2 - 5, y1 + 5, anchor="ne", text=f"L{level}",
                                       fill="#e6b655" if level == 2 else color, font=(font_family, 8, "bold"))
                caption = "PAUSED BY YOU" if game.paused[r][c] else "NEXT: OFFLINE" if (r, c) in offline else "HQ" if kind == "hq" else BUILDINGS[kind]["symbol"]
                canvas.create_text(cx, y2 - 4, anchor="s", text=translator(caption),
                                   fill="#ffb98d" if (r, c) in offline else color, font=(font_family, 8, "bold"))
            else:
                canvas.create_text(cx, cy + 4, text="+", fill="#42627d", font=("Segoe UI", 17))
