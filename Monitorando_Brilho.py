#!/usr/bin/env python3
# coding: utf-8
"""Monitor de brilho, SCT/gamma e frequência dos monitores."""

from __future__ import annotations

import re
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

HDMI_OUTPUT = "HDMI-1-0"
EDP_OUTPUT = "eDP-1"

REFRESH_MS = 2500

BACKLIGHT_DIR = Path("/sys/class/backlight/intel_backlight")
SCT_LOG = Path("/tmp/pos_Blue_Brilho.log")


# Tema escuro
BG = "#151719"
PANEL = "#202326"
PANEL_2 = "#292d31"
TEXT = "#e7e9eb"
MUTED = "#8c959f"
ACCENT = "#63c5d8"
IMPORTANT = "#ffd166"
GOOD = "#8bd17c"
ERROR = "#ff8b8b"


# ──────────────────────────────────────────────────────────────────────────────
# COMANDOS
# ──────────────────────────────────────────────────────────────────────────────

def run_command(*args: str) -> str:
    try:
        result = subprocess.run(
            args,
            text=True,
            capture_output=True,
            timeout=4,
            check=False,
        )
        return result.stdout if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def run_xrandr() -> str:
    return run_command("xrandr", "--verbose")


def run_xrandr_modes() -> str:
    return run_command("xrandr")


# ──────────────────────────────────────────────────────────────────────────────
# FREQUÊNCIA / RESOLUÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def parse_current_mode(
    xrandr_text: str,
    output_name: str,
) -> tuple[str | None, float | None]:
    """
    Obtém resolução e frequência atualmente ativas.

    Usa '*' para o modo atual e '+' como fallback, exatamente como no
    resolucao.sh usado pelo sistema.
    """
    lines = xrandr_text.splitlines()
    in_monitor = False
    resolution = None
    current = None
    preferred = None

    for line in lines:
        if re.match(rf"^{re.escape(output_name)}\s+connected\b", line):
            in_monitor = True

            # Ex.: HDMI-1-0 connected 1280x1024+1920+0 ...
            match = re.search(
                r"\b(\d+x\d+)\+\-?\d+\+\-?\d+\b",
                line,
            )
            if match:
                resolution = match.group(1)

            continue

        if in_monitor and line and not line[0].isspace():
            break

        if not in_monitor or not line[:1].isspace():
            continue

        # Ex.: 144.00*+ 120.00 60.00
        for match in re.finditer(
            r"(\d+(?:\.\d+)?)\s*(\*)?(\+)?",
            line,
        ):
            rate_text, star, plus = match.groups()

            if not (star or plus):
                continue

            rate = float(rate_text)

            if star and current is None:
                current = rate
            elif plus and preferred is None:
                preferred = rate

    refresh = current if current is not None else preferred
    return resolution, refresh


# ──────────────────────────────────────────────────────────────────────────────
# SCT
# ──────────────────────────────────────────────────────────────────────────────

def read_last_sct_temperature() -> str | None:
    """
    Lê a temperatura SCT do principal a partir de /tmp/pos_Blue_Brilho.log.

    Ordem de prioridade (de baixo para cima no log):
      1. Aplicação real:   sct 2700K → principal
      2. Fallback (skip):  Gamma principal 6500K OK → sct pulado

    O fallback é necessário após reinício: se o gamma já estiver correto,
    o Blue_Brilho não executa `sct` e só grava a mensagem de "pulado".
    Sem o fallback o mostrador ficaria "indisponível".
    """
    applied = re.compile(
        r"\bsct\s+(\d{4,5})\s*[kK]\s*→\s*principal\b",
        re.IGNORECASE,
    )
    skipped = re.compile(
        r"\bGamma\s+principal\s+(\d{4,5})\s*[kK]\s+OK\s*→\s*sct\s+pulado\b",
        re.IGNORECASE,
    )

    try:
        with SCT_LOG.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as log:
            lines = log.readlines()
    except OSError:
        return None

    # 1) Última aplicação real de sct
    for line in reversed(lines):
        match = applied.search(line)
        if match:
            return f"{int(match.group(1))} K"

    # 2) Fallback: última temperatura confirmada como OK (sct pulado)
    for line in reversed(lines):
        match = skipped.search(line)
        if match:
            return f"{int(match.group(1))} K"

    return None


# ──────────────────────────────────────────────────────────────────────────────
# XRANDR / BRILHO
# ──────────────────────────────────────────────────────────────────────────────

def output_block(
    xrandr_text: str,
    output_name: str,
) -> list[str]:
    lines = xrandr_text.splitlines()
    found = False
    block: list[str] = []

    for line in lines:
        if re.match(rf"^{re.escape(output_name)}\s", line):
            found = True
            block.append(line)
            continue

        if found and line and not line[0].isspace():
            break

        if found:
            block.append(line)

    return block


def parse_output(
    xrandr_text: str,
    output_name: str,
) -> tuple[str | None, float | None]:
    """Retorna Gamma RGB do xrandr e Brightness do output."""
    block = output_block(xrandr_text, output_name)

    if not block:
        return None, None

    gamma = None
    brightness = None

    for line in block:
        match = re.search(
            r"Gamma:\s*([\d.]+):([\d.]+):([\d.]+)",
            line,
        )
        if match:
            gamma = ":".join(match.groups())

        match = re.search(
            r"Brightness:\s*([\d.]+)",
            line,
        )
        if match:
            brightness = float(match.group(1))

    return gamma, brightness


def inverted_gamma(value: str | None) -> str | None:
    """Corrige o gamma invertido reportado por alguns drivers NVIDIA."""
    if not value:
        return None

    try:
        numbers = [float(part) for part in value.split(":")]
        return ":".join(
            f"{1 / number:.2f}" if number else "0.00"
            for number in numbers
        )
    except (ValueError, ZeroDivisionError):
        return None


def read_backlight() -> tuple[int | None, str | None]:
    try:
        current = int(
            (BACKLIGHT_DIR / "brightness").read_text().strip()
        )
        maximum = int(
            (BACKLIGHT_DIR / "max_brightness").read_text().strip()
        )

        if maximum <= 0:
            return None, None

        return round(current * 100 / maximum), f"{current}/{maximum}"
    except (OSError, ValueError, ZeroDivisionError):
        return None, None


def fmt(value: object, suffix: str = "") -> str:
    return f"{value}{suffix}" if value is not None else "indisponível"


# ──────────────────────────────────────────────────────────────────────────────
# INTERFACE
# ──────────────────────────────────────────────────────────────────────────────

class BrightnessApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__(className="Monitorando_Brilho")

        self.iconphoto(
            True,
            tk.PhotoImage(
                file="/usr/share/icons/Mint-X/apps/24/cs-screen.png"
            )
        )

        self.title("Brilho / Gamma")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", False)

        self._build_style()
        self._build_ui()
        self.refresh()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=BG)

        style.configure(
            "Panel.TFrame",
            background=PANEL,
        )

        style.configure(
            "TLabel",
            background=PANEL,
            foreground=TEXT,
            font=("DejaVu Sans", 9),
        )

        style.configure(
            "Header.TLabel",
            background=PANEL,
            foreground=ACCENT,
            font=("DejaVu Sans", 10, "bold"),
        )

        style.configure(
            "MainValue.TLabel",
            background=PANEL_2,
            foreground=IMPORTANT,
            font=("DejaVu Sans", 15, "bold"),
        )

        style.configure(
            "Value.TLabel",
            background=PANEL,
            foreground=TEXT,
            font=("DejaVu Sans", 9, "bold"),
        )

        style.configure(
            "Muted.TLabel",
            background=PANEL,
            foreground=MUTED,
            font=("DejaVu Sans", 8),
        )

        style.configure(
            "Good.TLabel",
            background=PANEL,
            foreground=GOOD,
            font=("DejaVu Sans", 9, "bold"),
        )

        style.configure(
            "Status.TLabel",
            background=BG,
            foreground=MUTED,
            font=("DejaVu Sans", 8),
        )

    def _build_ui(self) -> None:
        root = ttk.Frame(
            self,
            padding=(7, 6, 7, 4),
        )
        root.grid(sticky="nsew")

        title = tk.Label(
            root,
            text="☀  STATUS DE BRILHO / GAMMA",
            bg=BG,
            fg=ACCENT,
            font=("DejaVu Sans", 11, "bold"),
        )
        title.grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 5),
        )

        # ── MONITOR PRINCIPAL ────────────────────────────────────────────────
        self.main_panel = ttk.Frame(
            root,
            style="Panel.TFrame",
            padding=(8, 6, 8, 6),
        )
        self.main_panel.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 5),
        )

        ttk.Label(
            self.main_panel,
            text=f"▣  MONITOR PRINCIPAL  ·  {EDP_OUTPUT}",
            style="Header.TLabel",
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
        )

        ttk.Label(
            self.main_panel,
            text="Temperatura SCT",
            style="Muted.TLabel",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(4, 0),
        )

        self.gamma_main = ttk.Label(
            self.main_panel,
            text="—",
            style="MainValue.TLabel",
            padding=(7, 1),
        )
        self.gamma_main.grid(
            row=1,
            column=1,
            sticky="e",
            pady=(2, 0),
        )

        self.main_gamma_rgb = ttk.Label(
            self.main_panel,
            text="RGB xrandr: —",
            style="Muted.TLabel",
        )
        self.main_gamma_rgb.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(2, 0),
        )

        self.main_brightness = ttk.Label(
            self.main_panel,
            text="☀  Brilho: —",
            style="Value.TLabel",
        )
        self.main_brightness.grid(
            row=3,
            column=0,
            sticky="w",
            pady=(3, 0),
        )

        self.main_refresh = ttk.Label(
            self.main_panel,
            text="↻  — Hz",
            style="Good.TLabel",
        )
        self.main_refresh.grid(
            row=3,
            column=1,
            sticky="e",
            pady=(3, 0),
        )

        # ── MONITOR HDMI ─────────────────────────────────────────────────────
        self.hdmi_panel = ttk.Frame(
            root,
            style="Panel.TFrame",
            padding=(8, 6, 8, 6),
        )
        self.hdmi_panel.grid(
            row=2,
            column=0,
            sticky="ew",
        )

        ttk.Label(
            self.hdmi_panel,
            text=f"▣  MONITOR HDMI  ·  {HDMI_OUTPUT}",
            style="Header.TLabel",
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
        )

        self.hdmi_brightness = ttk.Label(
            self.hdmi_panel,
            text="☀  Brilho: —",
            style="Value.TLabel",
        )
        self.hdmi_brightness.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(4, 0),
        )

        self.hdmi_refresh = ttk.Label(
            self.hdmi_panel,
            text="↻  — Hz",
            style="Good.TLabel",
        )
        self.hdmi_refresh.grid(
            row=1,
            column=1,
            sticky="e",
            pady=(4, 0),
        )

        self.hdmi_gamma = ttk.Label(
            self.hdmi_panel,
            text="Gamma RGB: —",
            style="Muted.TLabel",
        )
        self.hdmi_gamma.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(3, 0),
        )

        # ── STATUS ───────────────────────────────────────────────────────────
        self.status = ttk.Label(
            root,
            text="Aguardando leitura…",
            style="Status.TLabel",
        )
        self.status.grid(
            row=3,
            column=0,
            sticky="w",
            pady=(4, 0),
        )

    def refresh(self) -> None:
        xrandr = run_xrandr()
        xrandr_modes = run_xrandr_modes()

        main_gamma_raw, main_brightness_xrandr = parse_output(
            xrandr,
            EDP_OUTPUT,
        )
        hdmi_gamma_raw, hdmi_brightness = parse_output(
            xrandr,
            HDMI_OUTPUT,
        )

        main_resolution, main_hz = parse_current_mode(
            xrandr_modes,
            EDP_OUTPUT,
        )
        hdmi_resolution, hdmi_hz = parse_current_mode(
            xrandr_modes,
            HDMI_OUTPUT,
        )

        sct_temperature = read_last_sct_temperature()
        backlight, detail = read_backlight()

        # SCT vem do pos_Blue_Brilho.log.
        # RGB continua sendo apenas a informação do xrandr.
        self.gamma_main.configure(
            text=fmt(sct_temperature),
        )

        self.main_gamma_rgb.configure(
            text=f"RGB xrandr: {fmt(main_gamma_raw)}",
        )

        self.main_brightness.configure(
            text=(
                f"☀  Brilho: {fmt(backlight, '%')}"
                + (f"  ({detail})" if detail else "")
            ),
        )

        main_mode = []
        if main_resolution:
            main_mode.append(main_resolution)
        if main_hz is not None:
            main_mode.append(f"{main_hz:.2f} Hz")

        self.main_refresh.configure(
            text=f"↻  {' @ '.join(main_mode) if main_mode else 'indisponível'}",
        )

        hdmi_percent = (
            round(hdmi_brightness * 100)
            if hdmi_brightness is not None
            else None
        )

        self.hdmi_brightness.configure(
            text=f"☀  Brilho: {fmt(hdmi_percent, '%')}",
        )

        hdmi_mode = []
        if hdmi_resolution:
            hdmi_mode.append(hdmi_resolution)
        if hdmi_hz is not None:
            hdmi_mode.append(f"{hdmi_hz:.2f} Hz")

        self.hdmi_refresh.configure(
            text=f"↻  {' @ '.join(hdmi_mode) if hdmi_mode else 'indisponível'}",
        )

        self.hdmi_gamma.configure(
            text=f"Gamma RGB: {fmt(inverted_gamma(hdmi_gamma_raw))}",
        )

        log_status = (
            "SCT: OK"
            if SCT_LOG.is_file()
            else "SCT: log não encontrado"
        )

        self.status.configure(
            text=(
                f"Atualizado a cada {REFRESH_MS / 1000:g} s"
                f"  ·  última leitura: {datetime.now().strftime('%H:%M:%S')}"
                f"  ·  {log_status}"
            ),
        )

        self.after(REFRESH_MS, self.refresh)


if __name__ == "__main__":
    BrightnessApp().mainloop()
