"""nova.py — NOVA v9 Autonomous OS Agent — Main entry point."""
import argparse
import logging
import sys
import threading
from pathlib import Path

# Configure logging before importing other modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("nova")


def health_check() -> bool:
    """Test all core modules before starting."""
    from rich.console import Console
    console = Console()
    ok = True
    checks = [
        ("config", "import config; print('OK')"),
        ("brain", "from core.brain import Brain"),
        ("executor", "from core.executor import Executor"),
        ("nova_loop", "from core.nova_loop import NOVALoop"),
        ("memory", "from core.memory import Memory"),
    ]
    console.print("\n[bold cyan]NOVA v9 — স্বাস্থ্য পরীক্ষা চলছে...[/bold cyan]")
    for name, code in checks:
        try:
            exec(code)
            console.print(f"  [green]✓[/green] {name}")
        except Exception as exc:
            console.print(f"  [red]✗[/red] {name}: {exc}")
            ok = False
    console.print()
    return ok


def run_cli(goal: str, dry_run: bool = False):
    """Run NOVA in text/CLI mode."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text

    from config import FEATURE_VOICE_OUTPUT, FEATURE_API_SERVER, API_SERVER_PORT, FEATURE_SAFETY
    from core.brain import Brain
    from core.executor import Executor
    from core.nova_loop import NOVALoop
    from core.memory import Memory

    console = Console()
    console.print(Panel.fit(
        "[bold magenta]NOVA v9[/bold magenta] — স্বায়ত্তশাসিত OS এজেন্ট",
        subtitle="[dim]ব্যক্তিগত ডিভাইস[/dim]",
    ))

    brain = Brain()
    executor = Executor()
    memory = Memory()
    tts = None

    if FEATURE_VOICE_OUTPUT:
        try:
            from modules.voice_tts import TTSQueue
            tts = TTSQueue()
            tts.start()
            logger.info("TTS চালু হয়েছে")
        except ImportError:
            logger.warning("TTS মডিউল পাওয়া যায়নি")

    # API server
    if FEATURE_API_SERVER:
        try:
            from modules.api_server import NovaAPIServer
            api = NovaAPIServer(port=API_SERVER_PORT)
            api.start()
        except Exception as exc:
            logger.warning(f"API সার্ভার শুরু ব্যর্থ: {exc}")

    nova = NOVALoop(brain=brain, executor=executor, memory=memory, tts=tts)

    # Wire callbacks
    nova.on_thought = lambda t: console.print(f"[dim cyan]💭 {t}[/dim cyan]")
    nova.on_tool_call = lambda name, args, result: console.print(
        f"[green]✓ {name}[/green] [dim]({result.get('_elapsed_s', 0):.1f}s)[/dim]\n"
        f"  [dim]{result.get('observation', '')[:200]}[/dim]"
    )
    nova.on_observation = lambda obs: console.print(f"[yellow]👁 {obs[:300]}[/yellow]")
    nova.on_complete = lambda msg: console.print(
        Panel(f"[bold green]✅ সম্পন্ন:[/bold green] {msg}", border_style="green")
    )
    nova.on_error = lambda err: console.print(f"[red]❌ ত্রুটি: {err}[/red]")

    if dry_run:
        console.print("[bold yellow]⚠ DRY-RUN মোড — কোনো পদক্ষেপ নেওয়া হবে না[/bold yellow]")

    console.print(f"\n[bold]লক্ষ্য:[/bold] {goal}\n")

    try:
        result = nova.run(goal, dry_run=dry_run)
        console.print(f"\n[bold green]চূড়ান্ত ফলাফল:[/bold green] {result}")
    except KeyboardInterrupt:
        nova.stop()
        console.print("\n[yellow]ব্যবহারকারী বন্ধ করেছেন।[/yellow]")


def run_interactive_cli():
    """Interactive REPL mode."""
    from rich.console import Console
    from rich.prompt import Prompt

    from config import FEATURE_VOICE_INPUT
    from core.brain import Brain
    from core.executor import Executor
    from core.nova_loop import NOVALoop
    from core.memory import Memory

    console = Console()
    console.print(Panel_safe("NOVA v9 — ইন্টারেক্টিভ মোড\n'exit' লিখলে বের হবে"))

    brain = Brain()
    executor = Executor()
    memory = Memory()
    nova = NOVALoop(brain=brain, executor=executor, memory=memory)

    nova.on_thought = lambda t: console.print(f"[dim cyan]💭 {t}[/dim cyan]")
    nova.on_tool_call = lambda n, a, r: console.print(
        f"[green]✓[/green] {n} → {r.get('observation', '')[:150]}"
    )
    nova.on_complete = lambda m: console.print(f"[bold green]✅[/bold green] {m}")

    # Voice input
    if FEATURE_VOICE_INPUT:
        try:
            from modules.voice_stt import VoiceListener
            vl = VoiceListener(callback=lambda text: _handle_voice(text, nova, console))
            vl.start()
            console.print("[cyan]🎤 ভয়েস ইনপুট সক্রিয় — 'নোভা' বলুন[/cyan]")
        except ImportError:
            logger.warning("STT মডিউল পাওয়া যায়নি")

    _task_thread: threading.Thread | None = None

    def _handle_voice(text: str, n: NOVALoop, c: Console):
        c.print(f"[cyan]🎤 শুনলাম:[/cyan] {text}")
        t = threading.Thread(target=n.run, args=(text,), daemon=True)
        t.start()

    while True:
        try:
            goal = Prompt.ask("\n[bold magenta]নোভা[/bold magenta]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]বিদায়![/yellow]")
            break

        if goal.strip().lower() in ("exit", "quit", "বের", "বিদায়"):
            console.print("[yellow]বিদায়![/yellow]")
            break

        if not goal.strip():
            continue

        if nova._stop_event.is_set():
            nova._stop_event.clear()

        _task_thread = threading.Thread(target=nova.run, args=(goal,), daemon=True)
        _task_thread.start()
        _task_thread.join()


def Panel_safe(text: str):
    try:
        from rich.panel import Panel
        return Panel(text)
    except ImportError:
        return text


def run_gui():
    """Launch the Tkinter GUI."""
    try:
        from ui_modern import ModernUI
        app = ModernUI()
        app.mainloop()
    except ImportError as exc:
        logger.error(f"UI লোড ব্যর্থ: {exc}")
        print("GUI চালু হয়নি। --text মোড ব্যবহার করুন।")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NOVA v9 — স্বায়ত্তশাসিত OS এজেন্ট")
    parser.add_argument("--text", action="store_true", help="CLI মোডে চালাও")
    parser.add_argument("--goal", type=str, help="সরাসরি লক্ষ্য দাও")
    parser.add_argument("--dry-run", action="store_true", help="DRY-RUN মোড")
    parser.add_argument("--no-health", action="store_true", help="স্বাস্থ্য পরীক্ষা বাদ দাও")
    args = parser.parse_args()

    if not args.no_health:
        if not health_check():
            logger.warning("কিছু মডিউল লোড হয়নি, তবু চালিয়ে যাচ্ছি...")

    if args.text or args.goal:
        if args.goal:
            run_cli(args.goal, dry_run=args.dry_run)
        else:
            run_interactive_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()
