"""ui_modern.py — Modern Tkinter UI for NOVA v9."""
import logging
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

logger = logging.getLogger(__name__)


class ModernUI(tk.Tk):
    """NOVA v9 Tkinter UI — non-blocking, Bengali interface."""

    def __init__(self):
        super().__init__()
        self.title("NOVA v9 — স্বায়ত্তশাসিত OS এজেন্ট")
        self.geometry("1100x700")
        self.configure(bg="#1a1a2e")

        self._nova = None
        self._task_thread: threading.Thread | None = None
        self._ui_queue: queue.Queue = queue.Queue()
        self._voice_active = False

        self._init_nova()
        self._build_ui()
        self._poll_queue()

    # ------------------------------------------------------------------
    # NOVA initialization
    # ------------------------------------------------------------------

    def _init_nova(self):
        try:
            from core.brain import Brain
            from core.executor import Executor
            from core.nova_loop import NOVALoop
            from core.memory import Memory

            brain = Brain()
            executor = Executor()
            memory = Memory()
            self._nova = NOVALoop(brain=brain, executor=executor, memory=memory)

            self._nova.on_thought = lambda t: self._ui_queue.put(("thought", t))
            self._nova.on_tool_call = lambda n, a, r: self._ui_queue.put(("tool", n, a, r))
            self._nova.on_observation = lambda o: self._ui_queue.put(("observation", o))
            self._nova.on_complete = lambda m: self._ui_queue.put(("complete", m))
            self._nova.on_error = lambda e: self._ui_queue.put(("error", e))
        except Exception as exc:
            logger.error(f"NOVA ইনিশিয়ালাইজ ব্যর্থ: {exc}")

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Color scheme
        BG = "#1a1a2e"
        SIDEBAR_BG = "#16213e"
        INPUT_BG = "#0f3460"
        TEXT_FG = "#e0e0e0"
        ACCENT = "#e94560"
        GREEN = "#00d4aa"
        YELLOW = "#ffd700"
        DIM = "#888888"

        # Main layout: sidebar + content
        main_frame = tk.Frame(self, bg=BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Sidebar ---
        sidebar = tk.Frame(main_frame, bg=SIDEBAR_BG, width=240)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="NOVA v9", bg=SIDEBAR_BG, fg=ACCENT,
                 font=("Arial", 14, "bold")).pack(pady=(15, 5))
        tk.Label(sidebar, text="স্বায়ত্তশাসিত OS এজেন্ট",
                 bg=SIDEBAR_BG, fg=DIM, font=("Arial", 9)).pack()

        ttk.Separator(sidebar, orient="horizontal").pack(fill=tk.X, padx=10, pady=10)

        # Current goal
        tk.Label(sidebar, text="বর্তমান লক্ষ্য:", bg=SIDEBAR_BG, fg=DIM,
                 font=("Arial", 9)).pack(anchor="w", padx=10)
        self._lbl_goal = tk.Label(sidebar, text="—", bg=SIDEBAR_BG, fg=TEXT_FG,
                                   font=("Arial", 9), wraplength=200, justify=tk.LEFT)
        self._lbl_goal.pack(anchor="w", padx=10, pady=(0, 5))

        # Current step
        tk.Label(sidebar, text="বর্তমান ধাপ:", bg=SIDEBAR_BG, fg=DIM,
                 font=("Arial", 9)).pack(anchor="w", padx=10)
        self._lbl_step = tk.Label(sidebar, text="—", bg=SIDEBAR_BG, fg=YELLOW,
                                   font=("Arial", 9), wraplength=200, justify=tk.LEFT)
        self._lbl_step.pack(anchor="w", padx=10, pady=(0, 10))

        ttk.Separator(sidebar, orient="horizontal").pack(fill=tk.X, padx=10, pady=5)

        # Cost stats
        tk.Label(sidebar, text="খরচ (এই সেশন):", bg=SIDEBAR_BG, fg=DIM,
                 font=("Arial", 9)).pack(anchor="w", padx=10)
        self._lbl_cost = tk.Label(sidebar, text="$0.000000", bg=SIDEBAR_BG, fg=GREEN,
                                   font=("Arial", 11, "bold"))
        self._lbl_cost.pack(anchor="w", padx=10)

        tk.Label(sidebar, text="API কল:", bg=SIDEBAR_BG, fg=DIM,
                 font=("Arial", 9)).pack(anchor="w", padx=10, pady=(5, 0))
        self._lbl_calls = tk.Label(sidebar, text="0", bg=SIDEBAR_BG, fg=TEXT_FG,
                                    font=("Arial", 9))
        self._lbl_calls.pack(anchor="w", padx=10)

        ttk.Separator(sidebar, orient="horizontal").pack(fill=tk.X, padx=10, pady=10)

        # Tool log
        tk.Label(sidebar, text="টুল লগ:", bg=SIDEBAR_BG, fg=DIM,
                 font=("Arial", 9)).pack(anchor="w", padx=10)
        self._tool_log = scrolledtext.ScrolledText(
            sidebar, bg="#0d0d1a", fg=GREEN, font=("Courier", 8),
            height=12, state=tk.DISABLED, wrap=tk.WORD,
        )
        self._tool_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Content area ---
        content = tk.Frame(main_frame, bg=BG)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Thought bubble (collapsible)
        thought_frame = tk.LabelFrame(
            content, text=" 💭 NOVA-র চিন্তা ", bg=BG, fg=DIM,
            font=("Arial", 9), bd=1, relief=tk.GROOVE,
        )
        thought_frame.pack(fill=tk.X, pady=(0, 5))
        self._thought_text = tk.Label(
            thought_frame, text="অপেক্ষা করছি...", bg=BG, fg=DIM,
            font=("Arial", 9, "italic"), wraplength=750, justify=tk.LEFT,
        )
        self._thought_text.pack(anchor="w", padx=10, pady=4)

        # Main chat area
        self._chat = scrolledtext.ScrolledText(
            content, bg="#0d0d1a", fg=TEXT_FG,
            font=("Arial", 11), state=tk.DISABLED,
            wrap=tk.WORD, padx=10, pady=10,
        )
        self._chat.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        # Tags for colored text
        self._chat.tag_config("user", foreground=ACCENT, font=("Arial", 11, "bold"))
        self._chat.tag_config("nova", foreground=GREEN)
        self._chat.tag_config("obs", foreground=YELLOW)
        self._chat.tag_config("error", foreground="#ff4444")
        self._chat.tag_config("done", foreground=GREEN, font=("Arial", 11, "bold"))

        # Input area
        input_frame = tk.Frame(content, bg=INPUT_BG, pady=6, padx=6)
        input_frame.pack(fill=tk.X)

        self._input = tk.Text(
            input_frame, bg=INPUT_BG, fg=TEXT_FG, insertbackground=TEXT_FG,
            font=("Arial", 11), height=2, wrap=tk.WORD,
            relief=tk.FLAT, padx=5, pady=5,
        )
        self._input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._input.bind("<Return>", self._on_send)
        self._input.bind("<Shift-Return>", lambda e: None)  # Allow newline

        btn_frame = tk.Frame(input_frame, bg=INPUT_BG)
        btn_frame.pack(side=tk.RIGHT, padx=(5, 0))

        self._btn_send = tk.Button(
            btn_frame, text="পাঠাও", bg=ACCENT, fg="white",
            font=("Arial", 10, "bold"), relief=tk.FLAT, padx=12, pady=6,
            command=self._on_send, cursor="hand2",
        )
        self._btn_send.pack(fill=tk.X, pady=(0, 3))

        self._btn_stop = tk.Button(
            btn_frame, text="বন্ধ করো", bg="#555", fg="white",
            font=("Arial", 10), relief=tk.FLAT, padx=12, pady=4,
            command=self._on_stop, cursor="hand2",
        )
        self._btn_stop.pack(fill=tk.X, pady=(0, 3))

        self._btn_voice = tk.Button(
            btn_frame, text="🎤 ভয়েস", bg="#333", fg=DIM,
            font=("Arial", 10), relief=tk.FLAT, padx=12, pady=4,
            command=self._toggle_voice, cursor="hand2",
        )
        self._btn_voice.pack(fill=tk.X)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_send(self, event=None):
        if event and event.state & 1:  # Shift held → newline
            return
        goal = self._input.get("1.0", tk.END).strip()
        if not goal:
            return "break"
        self._input.delete("1.0", tk.END)
        self._append_chat(f"আপনি: {goal}\n", "user")
        self._lbl_goal.config(text=goal[:60])
        self._run_task(goal)
        return "break"

    def _on_stop(self):
        if self._nova:
            self._nova.stop()
            self._append_chat("⏹ NOVA বন্ধ করা হয়েছে।\n", "error")

    def _toggle_voice(self):
        self._voice_active = not self._voice_active
        if self._voice_active:
            self._btn_voice.config(text="🎤 চালু", bg="#00d4aa", fg="black")
            self._start_voice()
        else:
            self._btn_voice.config(text="🎤 ভয়েস", bg="#333", fg="#888")
            self._stop_voice()

    def _start_voice(self):
        try:
            from modules.voice_stt import VoiceListener
            self._vl = VoiceListener(
                callback=lambda text: self._handle_voice_input(text)
            )
            self._vl.start()
        except ImportError:
            self._append_chat("ভয়েস মডিউল পাওয়া যায়নি।\n", "error")
            self._voice_active = False
            self._btn_voice.config(text="🎤 ভয়েস", bg="#333", fg="#888")

    def _stop_voice(self):
        if hasattr(self, "_vl"):
            self._vl.stop()

    def _handle_voice_input(self, text: str):
        self._ui_queue.put(("voice_input", text))

    # ------------------------------------------------------------------
    # Task execution (background thread)
    # ------------------------------------------------------------------

    def _run_task(self, goal: str):
        if self._task_thread and self._task_thread.is_alive():
            self._append_chat("⚠ আগের কাজ এখনও চলছে। বন্ধ করে নতুন শুরু করুন।\n", "error")
            return
        if self._nova and self._nova._stop_event.is_set():
            self._nova._stop_event.clear()

        def target():
            try:
                self._nova.run(goal)
            except Exception as exc:
                self._ui_queue.put(("error", str(exc)))

        self._task_thread = threading.Thread(target=target, daemon=True)
        self._task_thread.start()

    # ------------------------------------------------------------------
    # Chat helpers
    # ------------------------------------------------------------------

    def _append_chat(self, text: str, tag: str = "nova"):
        self._chat.config(state=tk.NORMAL)
        self._chat.insert(tk.END, text, tag)
        self._chat.see(tk.END)
        self._chat.config(state=tk.DISABLED)

    def _append_tool_log(self, text: str):
        self._tool_log.config(state=tk.NORMAL)
        self._tool_log.insert(tk.END, text)
        self._tool_log.see(tk.END)
        self._tool_log.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Queue polling (keeps UI responsive)
    # ------------------------------------------------------------------

    def _poll_queue(self):
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]

                if kind == "thought":
                    self._thought_text.config(text=item[1][:200])
                    self._lbl_step.config(text=item[1][:60])

                elif kind == "tool":
                    _, name, args, result = item
                    elapsed = result.get("_elapsed_s", 0)
                    obs = result.get("observation", "")[:100]
                    self._append_tool_log(f"✓ {name} ({elapsed:.1f}s)\n")
                    self._append_chat(f"[{name}] {obs}\n", "obs")
                    self._update_cost()

                elif kind == "observation":
                    self._append_chat(f"👁 {item[1][:300]}\n", "obs")

                elif kind == "complete":
                    self._append_chat(f"\n✅ সম্পন্ন: {item[1]}\n\n", "done")
                    self._lbl_step.config(text="সম্পন্ন ✅")
                    self._update_cost()

                elif kind == "error":
                    self._append_chat(f"❌ ত্রুটি: {item[1]}\n", "error")

                elif kind == "voice_input":
                    text = item[1]
                    self._append_chat(f"🎤 {text}\n", "user")
                    self._lbl_goal.config(text=text[:60])
                    self._run_task(text)

        except Exception:
            pass

        self.after(100, self._poll_queue)

    def _update_cost(self):
        try:
            if self._nova and self._nova.brain:
                summary = self._nova.brain.get_cost_summary()
                self._lbl_cost.config(text=f"${summary['total_cost_usd']:.6f}")
                self._lbl_calls.config(text=str(summary["calls"]))
        except Exception:
            pass
