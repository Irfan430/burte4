"""modules/cost_display.py — Cost tracking and display for NOVA."""
import logging
from typing import Any

from config import NOVA_COST_LIMIT

logger = logging.getLogger(__name__)

# Approximate cost per 1M tokens (USD)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "qwen/qwen2.5-coder-32b-instruct": {"input": 0.07, "output": 0.07},
    "google/gemini-flash-1.5": {"input": 0.075, "output": 0.30},
    "deepseek/deepseek-r1": {"input": 0.55, "output": 2.19},
    "qwen/qwen2.5-vl-7b-instruct": {"input": 0.10, "output": 0.10},
    "deepseek/deepseek-chat": {"input": 0.14, "output": 0.28},
}


class CostTracker:
    """Track API usage costs per model."""

    def __init__(self):
        self.usage: dict[str, dict[str, Any]] = {}
        self.total_cost: float = 0.0
        self._warned: bool = False

    def add_usage(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record token usage and return the cost for this call."""
        pricing = MODEL_PRICING.get(model, {"input": 0.5, "output": 1.5})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        if model not in self.usage:
            self.usage[model] = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0}

        self.usage[model]["input_tokens"] += input_tokens
        self.usage[model]["output_tokens"] += output_tokens
        self.usage[model]["cost_usd"] += cost
        self.usage[model]["calls"] += 1
        self.total_cost += cost

        logger.debug(f"খরচ: {model} | +${cost:.6f} | মোট: ${self.total_cost:.4f}")
        return cost

    def get_summary(self) -> dict[str, Any]:
        """Return a summary dict of all usage."""
        return {
            "total_cost_usd": round(self.total_cost, 6),
            "limit_usd": NOVA_COST_LIMIT,
            "remaining_usd": round(max(0.0, NOVA_COST_LIMIT - self.total_cost), 6),
            "percent_used": round((self.total_cost / NOVA_COST_LIMIT) * 100, 1) if NOVA_COST_LIMIT else 0,
            "models": {
                model: {
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "cost_usd": round(data["cost_usd"], 6),
                    "calls": data["calls"],
                }
                for model, data in self.usage.items()
            },
        }

    def print_summary(self) -> None:
        """Print a rich table summary of costs."""
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(title="NOVA খরচ সারসংক্ষেপ", show_header=True)
            table.add_column("মডেল", style="cyan")
            table.add_column("কল", justify="right")
            table.add_column("ইনপুট টোকেন", justify="right")
            table.add_column("আউটপুট টোকেন", justify="right")
            table.add_column("খরচ (USD)", justify="right", style="green")

            for model, data in self.usage.items():
                table.add_row(
                    model,
                    str(data["calls"]),
                    str(data["input_tokens"]),
                    str(data["output_tokens"]),
                    f"${data['cost_usd']:.6f}",
                )

            console.print(table)
            summary = self.get_summary()
            console.print(
                f"\n[bold]মোট খরচ:[/bold] [green]${summary['total_cost_usd']:.6f}[/green] / "
                f"[yellow]${summary['limit_usd']:.2f}[/yellow] সীমা "
                f"([red]{summary['percent_used']}%[/red] ব্যবহৃত)"
            )
        except ImportError:
            summary = self.get_summary()
            print(f"\n=== NOVA খরচ সারসংক্ষেপ ===")
            for model, data in self.usage.items():
                print(f"  {model}: {data['calls']} কল, ${data['cost_usd']:.6f}")
            print(f"মোট: ${summary['total_cost_usd']:.6f} / ${summary['limit_usd']:.2f}")

    def check_limit(self) -> bool:
        """Warn if approaching cost limit. Returns True if over limit."""
        if self.total_cost >= NOVA_COST_LIMIT:
            logger.error(
                f"খরচ সীমা অতিক্রম! ${self.total_cost:.4f} >= ${NOVA_COST_LIMIT:.2f}"
            )
            return True

        pct = self.total_cost / NOVA_COST_LIMIT if NOVA_COST_LIMIT else 0
        if pct >= 0.8 and not self._warned:
            logger.warning(
                f"সতর্কতা: খরচ সীমার {pct*100:.0f}% পৌঁছে গেছে! "
                f"${self.total_cost:.4f} / ${NOVA_COST_LIMIT:.2f}"
            )
            self._warned = True

        return False
