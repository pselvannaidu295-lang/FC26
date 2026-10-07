from __future__ import annotations

import csv
import json
import shutil
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any


STYLE_GROUPS = {
    "SCORING": (
        "Acrobatic", "Chip Shot", "Dead Ball", "Finesse Shot", "Power Header",
        "Power Shot", "Trivela",
    ),
    "PASSING": (
        "Incisive Pass", "Long Ball Pass", "Pinged Pass", "Tiki Taka", "Whipped Pass",
    ),
    "BALL CONTROL": (
        "First Touch", "Flair", "Press Proven", "Rapid", "Technical", "Trickster",
    ),
    "DEFENDING": (
        "Aerial Fortress", "Anticipate", "Block", "Bruiser", "Intercept", "Jockey",
        "Slide Tackle",
    ),
    "PHYSICAL": ("Aerial", "Enforcer", "Quick Step", "Relentless"),
    "GOALKEEPING": (
        "Cross Claimer", "Far Reach", "Far Throw", "Footwork", "Rush Out",
    ),
}


@dataclass
class Roster:
    players: list[dict[str, Any]]
    format: str
    container: Any
    player_key: str | None = None
    csv_fields: list[str] = field(default_factory=list)


def _validate_players(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("The roster must contain a list of player records.")
    if any(not isinstance(player, dict) for player in value):
        raise ValueError("Each player record must be an object with named fields.")
    return value


def load_roster(path: str | Path) -> Roster:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ValueError("The CSV file needs a header row.")
            players = [dict(row) for row in reader]
        return Roster(players, "csv", players, csv_fields=list(reader.fieldnames))
    if source.suffix.lower() != ".json":
        raise ValueError("Choose a .json or .csv roster file.")

    with source.open("r", encoding="utf-8-sig") as stream:
        content = json.load(stream)
    if isinstance(content, list):
        players = _validate_players(content)
        return Roster(players, "json", content)
    if isinstance(content, dict) and "players" in content:
        players = _validate_players(content["players"])
        return Roster(players, "json", content, player_key="players")
    raise ValueError('JSON must be a player list or an object containing a "players" list.')


def _style_list(value: Any, field_name: str) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        values = value.replace("|", ";").split(";")
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError(f'Player field "{field_name}" must be a list or a semicolon-separated string.')
    if any(not isinstance(style, str) for style in values):
        raise ValueError(f'Player field "{field_name}" can only contain style names as text.')
    return [style.strip() for style in values if style.strip()]


def apply_to_all(
    players: list[dict[str, Any]],
    playstyles: list[str],
    playstyles_plus: list[str],
    mode: str = "add",
) -> int:
    if mode not in {"add", "replace"}:
        raise ValueError('Mode must be "add" or "replace".')
    for player in players:
        _style_list(player.get("playstyles"), "playstyles")
        _style_list(player.get("playstyles_plus"), "playstyles_plus")
    changed = 0
    for player in players:
        for field_name, selected in (
            ("playstyles", playstyles),
            ("playstyles_plus", playstyles_plus),
        ):
            current = _style_list(player.get(field_name), field_name)
            if mode == "replace":
                updated = list(dict.fromkeys(selected))
            else:
                updated = list(current)
                seen = {style.casefold() for style in current}
                for style in selected:
                    if style.casefold() not in seen:
                        updated.append(style)
                        seen.add(style.casefold())
            player[field_name] = updated
        changed += 1
    return changed


def save_roster(roster: Roster, path: str | Path) -> None:
    destination = Path(path)
    if roster.format == "json":
        if roster.player_key:
            roster.container[roster.player_key] = roster.players
        with destination.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(roster.container, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return

    fields = list(roster.csv_fields)
    for field_name in ("playstyles", "playstyles_plus"):
        if field_name not in fields:
            fields.append(field_name)
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for player in roster.players:
            row = dict(player)
            for field_name in ("playstyles", "playstyles_plus"):
                row[field_name] = "; ".join(_style_list(row.get(field_name), field_name))
            writer.writerow(row)


def player_label(player: dict[str, Any], index: int) -> str:
    for key in ("player_name", "name", "long_name", "player_id", "id"):
        value = player.get(key)
        if value not in (None, ""):
            return str(value)
    return f"Player {index + 1}"


class PlaystyleEditor(tk.Tk):
    COLORS = {
        "ink": "#17242b",
        "muted": "#63727a",
        "paper": "#f3f5f1",
        "white": "#ffffff",
        "line": "#d8dfd9",
        "green": "#b8e05a",
        "orange": "#e87945",
        "blue": "#337b82",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title("FC26 Playstyle Editor")
        self.geometry("1120x760")
        self.minsize(920, 650)
        self.configure(bg=self.COLORS["paper"])
        self.roster: Roster | None = None
        self.source_path: Path | None = None
        self.applied = False
        self.mode = tk.StringVar(value="add")
        self.status = tk.StringVar(value="Open a CSV or JSON roster to begin.")
        self.base_vars: dict[str, tk.BooleanVar] = {}
        self.plus_vars: dict[str, tk.BooleanVar] = {}
        self.custom_styles: list[str] = []
        self._configure_styles()
        self._build_ui()
        self._render_catalog()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.COLORS["paper"])
        style.configure("Panel.TFrame", background=self.COLORS["white"])
        style.configure("TLabel", background=self.COLORS["paper"], foreground=self.COLORS["ink"], font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=self.COLORS["white"], foreground=self.COLORS["ink"], font=("Segoe UI", 10))
        style.configure("Muted.Panel.TLabel", background=self.COLORS["white"], foreground=self.COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=self.COLORS["ink"], foreground=self.COLORS["white"], font=("Segoe UI Semibold", 18))
        style.configure("Eyebrow.TLabel", background=self.COLORS["ink"], foreground=self.COLORS["green"], font=("Segoe UI Semibold", 9))
        style.configure("Section.TLabel", background=self.COLORS["white"], foreground=self.COLORS["muted"], font=("Segoe UI Semibold", 9))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(12, 8))
        style.configure("Accent.TButton", background=self.COLORS["green"], foreground=self.COLORS["ink"], borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#c9eb7d")])
        style.configure("Treeview", rowheight=29, font=("Segoe UI", 9), background=self.COLORS["white"], fieldbackground=self.COLORS["white"])
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background="#e9eee8", foreground=self.COLORS["ink"])
        style.configure("TRadiobutton", background=self.COLORS["white"], foreground=self.COLORS["ink"], font=("Segoe UI", 10))

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=self.COLORS["ink"], padx=24, pady=16)
        header.pack(fill="x")
        heading = tk.Frame(header, bg=self.COLORS["ink"])
        heading.pack(side="left", anchor="w")
        tk.Label(heading, text="FC26 / PC TOOL", bg=self.COLORS["ink"], fg=self.COLORS["green"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
        tk.Label(heading, text="Playstyle Editor", bg=self.COLORS["ink"], fg=self.COLORS["white"], font=("Segoe UI Semibold", 19)).pack(anchor="w")
        ttk.Button(header, text="Open roster", style="Accent.TButton", command=self.open_roster).pack(side="right", anchor="center")

        body = ttk.Frame(self, padding=(18, 18, 18, 12))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3, minsize=490)
        body.columnconfigure(1, weight=2, minsize=340)
        body.rowconfigure(0, weight=1)

        catalog = ttk.Frame(body, style="Panel.TFrame", padding=(16, 14))
        catalog.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        catalog.columnconfigure(0, weight=1)
        catalog.rowconfigure(3, weight=1)
        ttk.Label(catalog, text="PLAYSTYLE LIBRARY", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        tk.Label(catalog, text="Choose base styles and PlayStyle+ independently.", bg=self.COLORS["white"], fg=self.COLORS["muted"], font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=(4, 10))

        legend = tk.Frame(catalog, bg="#e9eee8", padx=8, pady=7)
        legend.grid(row=2, column=0, sticky="ew")
        legend.columnconfigure(0, weight=1)
        tk.Label(legend, text="STYLE", bg="#e9eee8", fg=self.COLORS["muted"], font=("Segoe UI Semibold", 8)).grid(row=0, column=0, sticky="w")
        tk.Label(legend, text="BASE", bg="#e9eee8", fg=self.COLORS["blue"], font=("Segoe UI Semibold", 8), width=7).grid(row=0, column=1)
        tk.Label(legend, text="PLUS", bg="#e9eee8", fg=self.COLORS["orange"], font=("Segoe UI Semibold", 8), width=7).grid(row=0, column=2)
        self.catalog_canvas = tk.Canvas(catalog, bg=self.COLORS["white"], highlightthickness=0)
        self.catalog_scroll = ttk.Scrollbar(catalog, orient="vertical", command=self.catalog_canvas.yview)
        self.catalog_inner = tk.Frame(self.catalog_canvas, bg=self.COLORS["white"])
        self.catalog_inner.bind("<Configure>", lambda _event: self.catalog_canvas.configure(scrollregion=self.catalog_canvas.bbox("all")))
        self.catalog_window = self.catalog_canvas.create_window((0, 0), window=self.catalog_inner, anchor="nw")
        self.catalog_canvas.configure(yscrollcommand=self.catalog_scroll.set)
        self.catalog_canvas.grid(row=3, column=0, sticky="nsew")
        self.catalog_scroll.grid(row=3, column=1, sticky="ns")
        self.catalog_inner.bind("<Enter>", lambda _event: self.catalog_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.catalog_inner.bind("<Leave>", lambda _event: self.catalog_canvas.unbind_all("<MouseWheel>"))
        self.catalog_canvas.bind("<Configure>", lambda event: self.catalog_canvas.itemconfigure(self.catalog_window, width=event.width))

        custom_row = ttk.Frame(catalog, style="Panel.TFrame")
        custom_row.grid(row=4, column=0, sticky="ew", pady=(9, 0))
        custom_row.columnconfigure(0, weight=1)
        self.custom_entry = ttk.Entry(custom_row)
        self.custom_entry.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        self.custom_entry.insert(0, "Add a custom style name")
        self.custom_entry.bind("<FocusIn>", self._clear_custom_placeholder)
        self.custom_target = tk.StringVar(value="base")
        ttk.Combobox(custom_row, textvariable=self.custom_target, values=("base", "plus"), state="readonly", width=7).grid(row=0, column=1, padx=(0, 7))
        ttk.Button(custom_row, text="Add", command=self.add_custom_style).grid(row=0, column=2)

        sidebar = ttk.Frame(body, style="Panel.TFrame", padding=16)
        sidebar.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(6, weight=1)
        ttk.Label(sidebar, text="ROSTER", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.roster_title = tk.Label(sidebar, text="No roster loaded", bg=self.COLORS["white"], fg=self.COLORS["ink"], font=("Segoe UI Semibold", 15), anchor="w", wraplength=330)
        self.roster_title.grid(row=1, column=0, sticky="ew", pady=(5, 2))
        self.roster_count = ttk.Label(sidebar, text="Open a CSV or JSON player export.", style="Muted.Panel.TLabel")
        self.roster_count.grid(row=2, column=0, sticky="w")

        ttk.Label(sidebar, text="APPLY MODE", style="Section.TLabel").grid(row=3, column=0, sticky="w", pady=(22, 8))
        mode_box = tk.Frame(sidebar, bg="#f3f5f1", padx=10, pady=8)
        mode_box.grid(row=4, column=0, sticky="ew")
        ttk.Radiobutton(mode_box, text="Add to existing", variable=self.mode, value="add").pack(anchor="w")
        ttk.Radiobutton(mode_box, text="Replace existing", variable=self.mode, value="replace").pack(anchor="w", pady=(5, 0))

        ttk.Label(sidebar, text="PREVIEW", style="Section.TLabel").grid(row=5, column=0, sticky="w", pady=(20, 8))
        self.preview = ttk.Treeview(sidebar, columns=("base", "plus"), show="tree headings", height=6)
        self.preview.heading("#0", text="Player")
        self.preview.heading("base", text="Base")
        self.preview.heading("plus", text="Plus")
        self.preview.column("#0", width=185, stretch=True)
        self.preview.column("base", width=48, anchor="center", stretch=False)
        self.preview.column("plus", width=48, anchor="center", stretch=False)
        self.preview.grid(row=6, column=0, sticky="nsew")

        self.apply_button = ttk.Button(sidebar, text="Apply to all players", style="Accent.TButton", command=self.apply_styles, state="disabled")
        self.apply_button.grid(row=7, column=0, sticky="ew", pady=(15, 7))
        self.export_button = ttk.Button(sidebar, text="Export updated roster...", command=self.export_roster, state="disabled")
        self.export_button.grid(row=8, column=0, sticky="ew")

        footer = tk.Frame(self, bg=self.COLORS["paper"], padx=22, pady=8)
        footer.pack(fill="x")
        tk.Label(footer, textvariable=self.status, bg=self.COLORS["paper"], fg=self.COLORS["muted"], font=("Segoe UI", 9), anchor="w").pack(fill="x")

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.catalog_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _clear_custom_placeholder(self, _event: tk.Event) -> None:
        if self.custom_entry.get() == "Add a custom style name":
            self.custom_entry.delete(0, "end")

    def _render_catalog(self) -> None:
        selected_base = {name: variable.get() for name, variable in self.base_vars.items()}
        selected_plus = {name: variable.get() for name, variable in self.plus_vars.items()}
        for child in self.catalog_inner.winfo_children():
            child.destroy()
        self.base_vars.clear()
        self.plus_vars.clear()
        groups = dict(STYLE_GROUPS)
        if self.custom_styles:
            groups["CUSTOM"] = tuple(self.custom_styles)
        row = 0
        for group_name, styles in groups.items():
            tk.Label(self.catalog_inner, text=group_name, bg=self.COLORS["white"], fg=self.COLORS["muted"], font=("Segoe UI Semibold", 8), padx=8, pady=7).grid(row=row, column=0, columnspan=3, sticky="w")
            row += 1
            for style_name in styles:
                base_var = tk.BooleanVar(value=selected_base.get(style_name, False))
                plus_var = tk.BooleanVar(value=selected_plus.get(style_name, False))
                self.base_vars[style_name] = base_var
                self.plus_vars[style_name] = plus_var
                tk.Label(self.catalog_inner, text=style_name, bg=self.COLORS["white"], fg=self.COLORS["ink"], font=("Segoe UI", 10), padx=8).grid(row=row, column=0, sticky="w")
                tk.Checkbutton(self.catalog_inner, variable=base_var, bg=self.COLORS["white"], activebackground=self.COLORS["white"], selectcolor="#e8f1da", fg=self.COLORS["blue"], padx=15).grid(row=row, column=1)
                tk.Checkbutton(self.catalog_inner, variable=plus_var, bg=self.COLORS["white"], activebackground=self.COLORS["white"], selectcolor="#fae9e2", fg=self.COLORS["orange"], padx=15).grid(row=row, column=2)
                row += 1

    def add_custom_style(self) -> None:
        style_name = self.custom_entry.get().strip()
        if not style_name or style_name == "Add a custom style name":
            return
        existing = {name.casefold() for name in self.base_vars}
        if style_name.casefold() in existing:
            messagebox.showinfo("Already listed", "That style is already in the library.")
            return
        self.custom_styles.append(style_name)
        self._render_catalog()
        target = self.base_vars if self.custom_target.get() == "base" else self.plus_vars
        target[style_name].set(True)
        self.custom_entry.delete(0, "end")

    def open_roster(self) -> None:
        path = filedialog.askopenfilename(
            title="Open player roster",
            filetypes=(("Roster files", "*.json *.csv"), ("JSON files", "*.json"), ("CSV files", "*.csv")),
        )
        if not path:
            return
        try:
            roster = load_roster(path)
        except (OSError, UnicodeError, json.JSONDecodeError, csv.Error, ValueError) as error:
            messagebox.showerror("Could not open roster", str(error))
            return
        if not roster.players:
            messagebox.showerror("Empty roster", "This file contains no player records.")
            return
        self.roster = roster
        self.source_path = Path(path).resolve()
        self.applied = False
        self.roster_title.configure(text=Path(path).name)
        self.roster_count.configure(text=f"{len(roster.players):,} players · {roster.format.upper()}")
        self.apply_button.configure(state="normal")
        self.export_button.configure(state="disabled")
        self.status.set("Roster loaded. Choose styles, then apply them to every player.")
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        for item in self.preview.get_children():
            self.preview.delete(item)
        if not self.roster:
            return
        for index, player in enumerate(self.roster.players[:6]):
            try:
                base_count = len(_style_list(player.get("playstyles"), "playstyles"))
                plus_count = len(_style_list(player.get("playstyles_plus"), "playstyles_plus"))
            except ValueError:
                base_count = plus_count = 0
            self.preview.insert("", "end", text=player_label(player, index), values=(base_count, plus_count))

    def apply_styles(self) -> None:
        if not self.roster:
            return
        base = [name for name, variable in self.base_vars.items() if variable.get()]
        plus = [name for name, variable in self.plus_vars.items() if variable.get()]
        if not base and not plus:
            messagebox.showwarning("No styles selected", "Choose at least one base or PlayStyle+ style first.")
            return
        try:
            changed = apply_to_all(self.roster.players, base, plus, self.mode.get())
        except ValueError as error:
            messagebox.showerror("Invalid roster data", str(error))
            return
        self.applied = True
        self.export_button.configure(state="normal")
        self._refresh_preview()
        self.status.set(f"Applied selected styles to {changed:,} players. Export to a new roster file.")

    def export_roster(self) -> None:
        if not self.roster or not self.applied or not self.source_path:
            return
        suffix = self.source_path.suffix.lower()
        initial_name = f"{self.source_path.stem}_playstyles{suffix}"
        path = filedialog.asksaveasfilename(
            title="Export updated roster",
            initialdir=str(self.source_path.parent),
            initialfile=initial_name,
            defaultextension=suffix,
            filetypes=((f"{suffix[1:].upper()} files", f"*{suffix}"),),
        )
        if not path:
            return
        destination = Path(path).resolve()
        if destination == self.source_path:
            if not messagebox.askyesno("Replace source file?", "This will replace your original roster. A .bak backup will be created first."):
                return
            try:
                shutil.copy2(self.source_path, self.source_path.with_suffix(self.source_path.suffix + ".bak"))
            except OSError as error:
                messagebox.showerror("Backup failed", str(error))
                return
        try:
            save_roster(self.roster, destination)
        except (OSError, ValueError) as error:
            messagebox.showerror("Export failed", str(error))
            return
        self.status.set(f"Exported {len(self.roster.players):,} players to {destination.name}.")
        messagebox.showinfo("Export complete", f"Updated roster saved to:\n{destination}")


if __name__ == "__main__":
    PlaystyleEditor().mainloop()