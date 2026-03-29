"""modules/mini_ui.py — Floating input overlay (like macOS Spotlight).

Triggered by Ctrl+Space hotkey anywhere in the OS.
A small centered input bar appears, user types command, presses Enter.
Disappears after submitting. Shows NOVA's response as notification.
"""
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class MiniUI:
    """Small floating overlay window for quick commands."""

    def __init__(self, on_submit: Callable[[str], None] | None = None):
        self.on_submit = on_submit or (lambda x: None)
        self._root = None

    def show(self):
        """Show the mini overlay (call from any thread)."""
        t = threading.Thread(target=self._run_window, daemon=True, name="mini-ui")
        t.start()

    def _run_window(self):
        try:
            import tkinter as tk
            from tkinter import font as tkfont

            root = tk.Tk()
            root.overrideredirect(True)        # No window decorations
            root.attributes("-topmost", True)  # Always on top
            root.attributes("-alpha", 0.95)    # Slight transparency
            root.configure(bg="#1a1a2e")

            # Center on screen
            w, h = 600, 60
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            x = (sw - w) // 2
            y = sh // 4
            root.geometry(f"{w}x{h}+{x}+{y}")

            # Rounded frame effect
            frame = tk.Frame(root, bg="#0f3460", padx=10, pady=8)
            frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

            # Icon label
            tk.Label(
                frame, text="◆ নোভা", bg="#0f3460", fg="#e94560",
                font=("Arial", 12, "bold"),
            ).pack(side=tk.LEFT, padx=(5, 10))

            # Input field
            entry_var = tk.StringVar()
            entry = tk.Entry(
                frame, textvariable=entry_var,
                bg="#0f3460", fg="white", insertbackground="white",
                font=("Arial", 13), relief=tk.FLAT, bd=0,
                width=40,
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry.focus_force()

            # Hint text
            hint = tk.Label(
                frame, text="Enter ↵", bg="#0f3460", fg="#555",
                font=("Arial", 10),
            )
            hint.pack(side=tk.RIGHT, padx=5)

            def _submit(event=None):
                goal = entry_var.get().strip()
                root.destroy()
                if goal:
                    threading.Thread(
                        target=self.on_submit, args=(goal,), daemon=True
                    ).start()

            def _cancel(event=None):
                root.destroy()

            entry.bind("<Return>", _submit)
            entry.bind("<Escape>", _cancel)

            # Close if focus lost
            root.bind("<FocusOut>", lambda e: root.after(200, _check_focus, root))

            def _check_focus(r):
                try:
                    if r.focus_get() is None:
                        r.destroy()
                except tk.TclError:
                    pass

            self._root = root
            root.mainloop()
        except ImportError as exc:
            logger.error(f"tkinter পাওয়া যায়নি: {exc}")
        except Exception as exc:
            logger.error(f"Mini UI ত্রুটি: {exc}")
