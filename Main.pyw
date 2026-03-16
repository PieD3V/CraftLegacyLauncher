import os
import sys
import json
import shutil
import requests
import zipfile
import tarfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, font as tkfont
from pathlib import Path
from configparser import ConfigParser
import subprocess
import logging
import time
import psutil
import random
from PIL import Image, ImageTk
import ctypes
from pathlib import Path

def load_font(font_path):
    FR_PRIVATE = 0x10
    if os.name == "nt":
        ctypes.windll.gdi32.AddFontResourceExW(str(font_path), FR_PRIVATE, 0)

try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False


logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('launcher.log')]
)
logger = logging.getLogger(__name__)


REPO = "smartcmd/MinecraftConsoles"
GITHUB_API = "https://api.github.com/repos"
INSTALL_DIR = Path.cwd() / "minecraft_install"
CONFIG_FILE = Path.cwd() / "launcher_config.ini"
VERSION_FILE = Path.cwd() / "version.txt"
BACKGROUND_IMAGE = Path.cwd() / "background.png"


INDEV_DIRT_BROWN = "#6b4c3b"
INDEV_DIRT_DARK = "#4f3a2b"
INDEV_STONE_GRAY = "#7f7f7f"
INDEV_STONE_DARK = "#555555"
INDEV_STONE_LIGHT = "#aaaaaa"
INDEV_BUTTON_BORDER = "#3f2f1f"
INDEV_TEXT = "#ffffff"
INDEV_TEXT_SHADOW = "#3f2f1f"
INDEV_YELLOW = "#ffff00" 

RANDOM_PHRASES = [
    "PieDEV was here!",
    "Creeper, aww man!",
    "SmartCMD is Smart!",
    "Microsoft got nothing on us!",
    "Message",
    "Too lazy to think of more phrases.",
    "Get good!",
    "Redstone is magic.",
    "OG Minecraft!",
    "Yippee!",
    "POV: Minecraft",
    "Hmm...",
]

class MinecraftLauncher:
    
    def __init__(self):
        self.config = ConfigParser()
        self.current_version = None
        self.latest_version = None
        self.install_path = INSTALL_DIR
        self.load_config()

    def load_config(self):
        if CONFIG_FILE.exists():
            self.config.read(CONFIG_FILE)
        else:
            self.config['Launcher'] = {'first_boot': 'true', 'install_path': str(INSTALL_DIR), 'version': '0.0.0'}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            self.config.write(f)

    def get_latest_version(self):
        try:
            url = f"{GITHUB_API}/{REPO}/releases/tags/nightly"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            version = data.get('tag_name', 'nightly').lstrip('v')
            if version == 'nightly':
                version = data.get('published_at', '0.0.0').split('T')[0]
            return version
        except Exception:
            return None

    def get_current_version(self):
        if VERSION_FILE.exists():
            with open(VERSION_FILE) as f:
                return f.read().strip()
        return "0.0.0"

    def save_version(self, version):
        if version:
            with open(VERSION_FILE, 'w') as f:
                f.write(str(version))

    def compare_versions(self, current, latest):
        try:
            if '-' in str(latest) or '-' in str(current):
                return int(str(latest).replace('-', '')) > int(str(current).replace('-', ''))
            cur = [int(x) for x in str(current).split('.')]
            lat = [int(x) for x in str(latest).split('.')]
            while len(cur) < len(lat):
                cur.append(0)
            while len(lat) < len(cur):
                lat.append(0)
            return lat > cur
        except Exception:
            return True

    def download_release(self, progress_callback=None):
        try:
            if progress_callback:
                progress_callback("Fetching release...", 0)
            url = f"{GITHUB_API}/{REPO}/releases/tags/nightly"
            data = requests.get(url, timeout=10).json()
            assets = data.get('assets', [])
            if not assets:
                return None
            asset = next((a for a in assets if 'LCEWindows64' in a['name']), assets[0])
            download_url = asset['browser_download_url']
            name = asset['name']
            if progress_callback:
                progress_callback(f"Downloading {name}...", 5)
            r = requests.get(download_url, stream=True, timeout=60)
            r.raise_for_status()
            path = Path.cwd() / name
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total and progress_callback:
                        progress_callback(f"Downloading {name}...", 5 + int(45 * downloaded / total))
            return path
        except Exception:
            return None

    def extract_archive(self, archive_path, progress_callback=None):
        try:
            if progress_callback:
                progress_callback("Extracting...", 50)
            self.install_path.mkdir(parents=True, exist_ok=True)
            if str(archive_path).endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as z:
                    z.extractall(self.install_path)
            else:
                with tarfile.open(archive_path, 'r:gz') as t:
                    t.extractall(self.install_path)
            if progress_callback:
                progress_callback("Cleaning up...", 75)
            archive_path.unlink()
            return True
        except Exception:
            return False

    def install_game(self, progress_callback=None):
        try:
            self.latest_version = self.get_latest_version()
            if not self.latest_version:
                return False
            archive = self.download_release(progress_callback)
            if not archive:
                return False
            if self.install_path.exists():
                shutil.rmtree(self.install_path)
            if not self.extract_archive(archive, progress_callback):
                return False
            self.save_version(self.latest_version)
            if progress_callback:
                progress_callback("Done!", 100)
            return True
        except Exception:
            return False

    def find_executable(self):
        candidates = ['Minecraft.Client.exe', 'LCEWindows.exe', 'MinecraftConsoles.exe', 'minecraft.exe']
        for exe in candidates:
            if (self.install_path / exe).exists():
                return self.install_path / exe
        for exe in self.install_path.rglob('*.exe'):
            return exe
        return None

    def load_playtime(self):
        try:
            if 'Playtime' not in self.config:
                self.config.add_section('Playtime')
            return self.config['Playtime'].getint('total_seconds', 0)
        except Exception:
            return 0

    def save_playtime(self, seconds):
        try:
            if 'Playtime' not in self.config:
                self.config.add_section('Playtime')
            self.config['Playtime']['total_seconds'] = str(seconds)
            self.save_config()
        except Exception:
            pass

    def format_playtime(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m" if h else f"{m}m"

    def launch_game(self, username=None, ip=None):
        exe = self.find_executable()
        if not exe:
            return False
        cmd = [str(exe)]
        if username and ip:
            cmd.extend(['-name', username, '-ip', ip, '-port', '25566'])
        try:
            proc = subprocess.Popen(cmd, cwd=str(self.install_path))
            threading.Thread(target=self._monitor, args=(proc.pid,), daemon=True).start()
            return True
        except Exception:
            return False

    def _monitor(self, pid):
        try:
            start = time.time()
            psutil.Process(pid).wait()
            session = int(time.time() - start)
            total = self.load_playtime() + session
            self.save_playtime(total)
        except Exception:
            pass

    def uninstall_game(self):
        try:
            if self.install_path.exists():
                if HAS_SEND2TRASH:
                    send2trash(str(self.install_path))
                else:
                    shutil.rmtree(self.install_path)
            if VERSION_FILE.exists():
                (HAS_SEND2TRASH and send2trash(str(VERSION_FILE))) or VERSION_FILE.unlink()
            return True
        except Exception:
            return False


class IndevGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft LCE Launcher")
        self.root.geometry("1000x800")
        self.root.resizable(False, False)

        self.launcher = MinecraftLauncher()
        self.launcher.current_version = self.launcher.get_current_version()
        self.total_playtime = self.launcher.load_playtime()

        self.load_custom_font()
        self.create_ui()
        self.check_first_boot()

    def load_custom_font(self):
     font_path = Path.cwd() / "Minecraftia-Regular.ttf"

     if font_path.exists():
        load_font(font_path)
        target_font = "Minecraftia"
     else:
        target_font = "Arial"

     self.fonts = {
        "normal": tkfont.Font(family=target_font, size=10),
        "bold": tkfont.Font(family=target_font, size=10, weight="bold"),
        "medium": tkfont.Font(family=target_font, size=12),
        "large_bold": tkfont.Font(family=target_font, size=18, weight="bold"),
        "title": tkfont.Font(family=target_font, size=28, weight="bold"),
        "title_shadow": tkfont.Font(family=target_font, size=28, weight="bold"),
        "small": tkfont.Font(family=target_font, size=9),
    }

    def apply_background(self, parent):
        
        if BACKGROUND_IMAGE.exists():
            try:
                img = Image.open(BACKGROUND_IMAGE).resize((1000, 800), Image.Resampling.LANCZOS)
                self.bg_image_ref = ImageTk.PhotoImage(img)
                bg = tk.Label(parent, image=self.bg_image_ref)
                bg.place(x=0, y=0, relwidth=1, relheight=1)
                bg.lower() 
            except Exception as e:
                logger.warning(f"Background image failed: {e}")

    def update_random_phrase(self):
        phrase = random.choice(RANDOM_PHRASES)
        self.phrase_label.config(text=phrase)

    def create_ui(self):
        
        main = tk.Frame(self.root, bg=INDEV_DIRT_BROWN)
        main.place(relwidth=1, relheight=1)

        
        self.apply_background(main)

        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=INDEV_DIRT_BROWN, borderwidth=0)
        style.configure('TNotebook.Tab', background=INDEV_DIRT_BROWN, foreground=INDEV_TEXT,
                        padding=[10, 5], font=self.fonts['bold'])
        style.map('TNotebook.Tab', background=[('selected', INDEV_STONE_GRAY)])

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.main_tab = tk.Frame(self.notebook, bg=INDEV_DIRT_BROWN)
        self.settings_tab = tk.Frame(self.notebook, bg=INDEV_DIRT_BROWN)
        self.notebook.add(self.main_tab, text="Main")
        self.notebook.add(self.settings_tab, text="Settings")

        self.create_main_tab()
        self.create_settings_tab()

        prog_frame = tk.Frame(main, bg=INDEV_DIRT_BROWN)
        prog_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.progress_var, maximum=100,
                                            mode='determinate', style='Indev.Horizontal.TProgressbar')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        self.status_text = tk.Label(prog_frame, text="Ready", bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT,
                                    font=self.fonts['small'], anchor='w')
        self.status_text.pack(fill=tk.X)

        self.phrase_label = tk.Label(prog_frame, text="", bg=INDEV_DIRT_BROWN, fg=INDEV_YELLOW,
                                     font=self.fonts['bold'], anchor='center')
        self.phrase_label.pack(fill=tk.X, pady=(0, 5))
        self.update_random_phrase()  
        self.phrase_label.bind("<Button-1>", lambda e: self.update_random_phrase())

        style.configure('Indev.Horizontal.TProgressbar',
                        background=INDEV_STONE_LIGHT, troughcolor=INDEV_STONE_DARK,
                        bordercolor=INDEV_STONE_DARK, lightcolor=INDEV_STONE_LIGHT,
                        darkcolor=INDEV_STONE_DARK)

    def create_main_tab(self):
        title_frame = tk.Frame(self.main_tab, bg=INDEV_DIRT_BROWN)
        title_frame.pack(pady=(30, 10))
        shadow = tk.Label(title_frame, text="Minecraft LCE Launcher", bg=INDEV_DIRT_BROWN,
                          fg=INDEV_TEXT_SHADOW, font=self.fonts['title_shadow'])
        shadow.place(x=3, y=3)
        title = tk.Label(title_frame, text="Minecraft LCE Launcher", bg=INDEV_DIRT_BROWN,
                         fg=INDEV_TEXT, font=self.fonts['title'])
        title.pack()

        info = tk.Frame(self.main_tab, bg=INDEV_DIRT_BROWN)
        info.pack(pady=20)
        self.version_text = tk.Label(info, text=f"Installed: {self.launcher.current_version}",
                                     bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT, font=self.fonts['medium'])
        self.version_text.pack()
        self.playtime_text = tk.Label(info, text=f"Total Playtime: {self.launcher.format_playtime(self.total_playtime)}",
                                      bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT, font=self.fonts['medium'])
        self.playtime_text.pack(pady=(5, 0))

        self.play_btn = self.stone_button(self.main_tab, text="PLAY", command=self.on_launch,
                                          width=20, height=2, font=self.fonts['large_bold'])
        self.play_btn.pack(pady=30)

        action = tk.Frame(self.main_tab, bg=INDEV_DIRT_BROWN)
        action.pack()
        self.check_btn = self.stone_button(action, text="Check Updates", command=self.on_check_updates, width=15)
        self.check_btn.pack(side=tk.LEFT, padx=5)
        self.reinstall_btn = self.stone_button(action, text="Reinstall", command=self.on_reinstall, width=10)
        self.reinstall_btn.pack(side=tk.LEFT, padx=5)
        self.uninstall_btn = self.stone_button(action, text="Uninstall", command=self.on_uninstall, width=10, fg="#ffaaaa")
        self.uninstall_btn.pack(side=tk.LEFT, padx=5)

        self.stone_button(self.main_tab, text="Quit", command=self.on_exit, width=8).pack(side=tk.BOTTOM, anchor='se', padx=20, pady=20)

    def create_settings_tab(self):
        path_frame = tk.Frame(self.settings_tab, bg=INDEV_DIRT_BROWN)
        path_frame.pack(fill=tk.X, padx=30, pady=(30, 10))
        tk.Label(path_frame, text="Installation Path:", bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT,
                 font=self.fonts['bold']).pack(anchor='w')
        disp = tk.Frame(path_frame, bg=INDEV_DIRT_BROWN)
        disp.pack(fill=tk.X, pady=5)
        self.path_entry = tk.Entry(disp, bg=INDEV_STONE_DARK, fg=INDEV_TEXT, font=self.fonts['normal'],
                                    bd=2, relief=tk.SUNKEN, state='readonly')
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        self.path_entry.configure(textvariable=tk.StringVar(value=str(self.launcher.install_path)))
        self.stone_button(disp, text="Locate", command=self.on_locate_installation, width=8).pack(side=tk.RIGHT, padx=(10, 0))

        lan = tk.Frame(self.settings_tab, bg=INDEV_DIRT_BROWN)
        lan.pack(fill=tk.X, padx=30, pady=20)
        tk.Label(lan, text="LAN Play", bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT,
                 font=self.fonts['bold']).pack(anchor='w')
        btn_frame = tk.Frame(lan, bg=INDEV_DIRT_BROWN)
        btn_frame.pack(fill=tk.X, pady=10)
        self.lan_toggle = self.stone_button(btn_frame, text="Enable LAN Play", command=self.on_lan_toggle, width=15)
        self.lan_toggle.pack(side=tk.LEFT, padx=(0, 10))
        self.lan_settings = self.stone_button(btn_frame, text="LAN Settings", command=self.on_lan_settings, width=12)
        self.lan_settings.pack(side=tk.LEFT)
        self.lan_status = tk.Label(lan, text="LAN Play is disabled", bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT,
                                    font=self.fonts['normal'])
        self.lan_status.pack(anchor='w', pady=(5, 0))

        self.load_lan_settings()

    def stone_button(self, parent, text, command, width=None, height=None, font=None, fg=INDEV_TEXT):
        if font is None:
            font = self.fonts['bold']
        btn = tk.Button(parent, text=text, bg=INDEV_STONE_GRAY, fg=fg, font=font,
                        relief=tk.RAISED, bd=3, padx=10, pady=5, cursor="hand2",
                        activebackground=INDEV_STONE_LIGHT, activeforeground=fg)
        btn.config(command=command)
        if width:
            btn.config(width=width)
        if height:
            btn.config(height=height)
        return btn

    def update_progress(self, msg, val):
        self.status_text.config(text=msg)
        self.progress_var.set(val)
        self.root.update()

    def show_info(self, title, msg):
        d = tk.Toplevel(self.root)
        d.title(title)
        d.geometry("500x250")
        d.resizable(False, False)
        d.configure(bg=INDEV_DIRT_BROWN)
        d.grab_set()
        tk.Label(d, text=title, bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT, font=self.fonts['large_bold']).pack(anchor='w', padx=30, pady=(30, 20))
        tk.Label(d, text=msg, bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT, font=self.fonts['medium'], wraplength=440, justify=tk.LEFT).pack(anchor='w', padx=30, pady=(0, 30))
        f = tk.Frame(d, bg=INDEV_DIRT_BROWN)
        f.pack(fill=tk.X, padx=30, pady=(0, 30), anchor='e')
        self.stone_button(f, text="OK", command=d.destroy, width=8).pack(side=tk.RIGHT)

    def show_confirm(self, title, msg, on_yes, on_no=None):
        d = tk.Toplevel(self.root)
        d.title(title)
        d.geometry("500x250")
        d.resizable(False, False)
        d.configure(bg=INDEV_DIRT_BROWN)
        d.grab_set()
        tk.Label(d, text=title, bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT, font=self.fonts['large_bold']).pack(anchor='w', padx=30, pady=(30, 20))
        tk.Label(d, text=msg, bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT, font=self.fonts['medium'], wraplength=440, justify=tk.LEFT).pack(anchor='w', padx=30, pady=(0, 30))
        f = tk.Frame(d, bg=INDEV_DIRT_BROWN)
        f.pack(fill=tk.X, padx=30, pady=(0, 30), anchor='e')
        self.stone_button(f, text="Yes", command=lambda: [d.destroy(), on_yes()], width=8).pack(side=tk.RIGHT, padx=(10, 0))
        self.stone_button(f, text="No", command=lambda: [d.destroy(), on_no() if on_no else None], width=8).pack(side=tk.RIGHT)

    def check_first_boot(self):
        if self.launcher.config['Launcher'].getboolean('first_boot', True):
            self.first_boot_dialog()

    def first_boot_dialog(self):
        d = tk.Toplevel(self.root)
        d.title("Welcome")
        d.geometry("600x400")
        d.resizable(False, False)
        d.configure(bg=INDEV_DIRT_BROWN)
        d.grab_set()
        tk.Label(d, text="Welcome!", bg=INDEV_DIRT_BROWN,
                 fg=INDEV_TEXT, font=self.fonts['title']).pack(anchor='w', padx=30, pady=(30, 10))
        tk.Label(d, text="What would you like to do?", bg=INDEV_DIRT_BROWN,
                 fg=INDEV_TEXT, font=self.fonts['medium']).pack(anchor='w', padx=30, pady=(0, 30))
        f = tk.Frame(d, bg=INDEV_DIRT_BROWN)
        f.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 30))
        self.stone_button(f, text="Install Latest Build", command=lambda: [d.destroy(), self.on_install_new()],
                          width=25, height=2, font=self.fonts['large_bold']).pack(fill=tk.X, pady=(0, 15))
        self.stone_button(f, text="Locate Existing Installation", command=lambda: [d.destroy(), self.on_locate_installation()],
                          width=25, height=2, font=self.fonts['large_bold']).pack(fill=tk.X)

    def load_lan_settings(self):
        if 'LAN' not in self.launcher.config:
            self.launcher.config.add_section('LAN')
        self.lan_enabled = self.launcher.config['LAN'].getboolean('enabled', False)
        self.lan_username = self.launcher.config['LAN'].get('username', '')
        self.lan_ip = self.launcher.config['LAN'].get('ip', '')
        self.update_lan_state()

    def save_lan_settings(self):
        self.launcher.config['LAN']['enabled'] = str(self.lan_enabled)
        self.launcher.config['LAN']['username'] = self.lan_username
        self.launcher.config['LAN']['ip'] = self.lan_ip
        self.launcher.save_config()

    def update_lan_state(self):
        if self.lan_enabled:
            self.lan_toggle.config(text="Disable LAN Play")
            self.lan_settings.config(state=tk.NORMAL)
            self.lan_status.config(text=f"LAN Play enabled: {self.lan_username} @ {self.lan_ip}")
        else:
            self.lan_toggle.config(text="Enable LAN Play")
            self.lan_settings.config(state=tk.DISABLED)
            self.lan_status.config(text="LAN Play is disabled")

    def on_lan_toggle(self):
        if not self.lan_enabled:
            self.lan_setup_dialog()
        else:
            self.lan_enabled = False
            self.save_lan_settings()
            self.update_lan_state()
            self.show_info("LAN Play Disabled", "LAN Play mode has been disabled.")

    def lan_setup_dialog(self):
        d = tk.Toplevel(self.root)
        d.title("LAN Play Setup")
        d.geometry("500x350")
        d.resizable(False, False)
        d.configure(bg=INDEV_DIRT_BROWN)
        d.grab_set()
        tk.Label(d, text="LAN Play Setup", bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT,
                 font=self.fonts['large_bold']).pack(anchor='w', padx=30, pady=(30, 10))
        tk.Label(d, text="Enter your username and LAN IP", bg=INDEV_DIRT_BROWN,
                 fg=INDEV_TEXT, font=self.fonts['medium']).pack(anchor='w', padx=30, pady=(0, 20))

        tk.Label(d, text="Username:", bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT,
                 font=self.fonts['bold']).pack(anchor='w', padx=30, pady=(0, 5))
        user_entry = tk.Entry(d, font=self.fonts['normal'], width=40, bg=INDEV_STONE_DARK,
                               fg=INDEV_TEXT, bd=2, relief=tk.SUNKEN)
        user_entry.pack(anchor='w', padx=30, pady=(0, 15))
        if self.lan_username:
            user_entry.insert(0, self.lan_username)

        tk.Label(d, text="LAN IP:", bg=INDEV_DIRT_BROWN, fg=INDEV_TEXT,
                 font=self.fonts['bold']).pack(anchor='w', padx=30, pady=(0, 5))
        ip_entry = tk.Entry(d, font=self.fonts['normal'], width=40, bg=INDEV_STONE_DARK,
                            fg=INDEV_TEXT, bd=2, relief=tk.SUNKEN)
        ip_entry.pack(anchor='w', padx=30, pady=(0, 30))
        if self.lan_ip:
            ip_entry.insert(0, self.lan_ip)

        btn_frame = tk.Frame(d, bg=INDEV_DIRT_BROWN)
        btn_frame.pack(fill=tk.X, padx=30, pady=(0, 30), anchor='e')
        def confirm():
            u = user_entry.get().strip()
            i = ip_entry.get().strip()
            if not u or not i:
                self.show_info("Invalid Input", "Both fields are required.")
                return
            self.lan_username = u
            self.lan_ip = i
            self.lan_enabled = True
            self.save_lan_settings()
            self.update_lan_state()
            d.destroy()
            self.show_info("LAN Play Enabled", f"Username: {u}\nServer IP: {i}")
        self.stone_button(btn_frame, text="Enable", command=confirm, width=10).pack(side=tk.RIGHT, padx=(10, 0))
        self.stone_button(btn_frame, text="Cancel", command=d.destroy, width=10).pack(side=tk.RIGHT)

    def on_lan_settings(self):
        if self.lan_enabled:
            self.lan_setup_dialog()
        else:
            self.show_info("LAN Play Not Enabled", "Please enable LAN Play first.")

    def on_install_new(self):
        self.launcher.latest_version = self.launcher.get_latest_version()
        if not self.launcher.latest_version:
            self.show_info("Error", "Could not fetch latest version.")
            return
        self.install_thread = threading.Thread(target=self._install_thread)
        self.install_thread.daemon = True
        self.install_thread.start()

    def _install_thread(self):
        for btn in [self.check_btn, self.reinstall_btn, self.play_btn]:
            btn.config(state=tk.DISABLED)
        if self.launcher.install_game(self.update_progress):
            self.launcher.config['Launcher']['first_boot'] = 'false'
            self.launcher.save_config()
            self.root.after(0, lambda: self.show_info("Success", "Installation completed!"))
            self.root.after(0, self.refresh_ui)
        else:
            self.root.after(0, lambda: self.show_info("Error", "Installation failed."))
        self.root.after(0, lambda: [btn.config(state=tk.NORMAL) for btn in [self.check_btn, self.reinstall_btn, self.play_btn]])

    def on_locate_installation(self):
        folder = filedialog.askdirectory(title="Select installation folder")
        if not folder:
            return
        p = Path(folder)
        if self.find_executable_in_path(p):
            self.launcher.install_path = p
            self.launcher.config['Launcher']['install_path'] = str(p)
            self.launcher.config['Launcher']['first_boot'] = 'false'
            self.launcher.save_config()
            self.show_info("Success", f"Installation located at:\n{p}")
            self.refresh_ui()
        else:
            self.show_info("Error", "No game executable found in that folder.")

    def find_executable_in_path(self, folder):
        for exe in ['Minecraft.Client.exe', 'LCEWindows.exe', 'MinecraftConsoles.exe', 'minecraft.exe']:
            if (folder / exe).exists():
                return folder / exe
        return None

    def on_launch(self):
        if not self.launcher.install_path.exists():
            self.show_info("Error", "Game not installed.")
            return
        ok = self.launcher.launch_game(self.lan_username if self.lan_enabled else None,
                                       self.lan_ip if self.lan_enabled else None)
        if ok:
            self.show_info("")
        else:
            self.show_info("Error", "Launch failed.")

    def on_check_updates(self):
        self.update_progress("Checking...", 0)
        latest = self.launcher.get_latest_version()
        current = self.launcher.get_current_version()
        self.update_progress("Ready", 0)
        if not latest:
            self.show_info("Error", "Could not fetch latest version.")
            return
        if self.launcher.compare_versions(current, latest):
            self.show_confirm("Update Available",
                              f"Current: {current}\nLatest: {latest}\n\nDownload and install?",
                              lambda: [setattr(self.launcher, 'latest_version', latest), self.on_reinstall()])
        else:
            self.show_info("Up to Date", f"You are on the latest version: {current}")

    def on_reinstall(self):
        self.show_confirm("Reinstall", "Download and reinstall the latest version?", self.on_install_new)

    def on_uninstall(self):
        if not self.launcher.install_path.exists():
            self.show_info("Not Installed", "Game is not installed.")
            return
        self.show_confirm("Uninstall", "Remove all game files?", lambda: self._do_uninstall())

    def _do_uninstall(self):
        if self.launcher.uninstall_game():
            self.show_info("Success", "Game uninstalled.")
            self.refresh_ui()
        else:
            self.show_info("Error", "Uninstall failed.")

    def on_exit(self):
        self.root.quit()

    def refresh_ui(self):
        self.launcher.current_version = self.launcher.get_current_version()
        self.version_text.config(text=f"Installed: {self.launcher.current_version}")
        self.total_playtime = self.launcher.load_playtime()
        self.playtime_text.config(text=f"Total Playtime: {self.launcher.format_playtime(self.total_playtime)}")
        self.status_text.config(text="Ready")
        self.progress_var.set(0)
        self.path_entry.config(state='normal')
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, str(self.launcher.install_path))
        self.path_entry.config(state='readonly')
        self.load_lan_settings()
        self.update_random_phrase()

def main():
    root = tk.Tk()
    _ = IndevGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
