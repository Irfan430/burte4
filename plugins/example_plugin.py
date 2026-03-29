"""example_plugin.py — Template for NOVA v9 plugins.

Copy this file to plugins/ and implement your own tools.
Each plugin must have a `register()` function returning a dict of tool_name → callable.
"""
from datetime import datetime


def hello_world() -> dict:
    """Example tool: returns a greeting."""
    return {"observation": f"হ্যালো ওয়ার্ল্ড! সময়: {datetime.now().strftime('%H:%M:%S')}", "display": None}


def get_date() -> dict:
    """Example tool: returns today's date."""
    return {"observation": f"আজকের তারিখ: {datetime.now().strftime('%Y-%m-%d')}", "display": None}


def register() -> dict:
    """Return mapping of tool_name → function."""
    return {
        "hello_world": hello_world,
        "get_date": get_date,
    }
