import os
import sys
import ctypes
import requests
import zipfile
import subprocess
import threading
import pystray
import shutil
from PIL import Image
import customtkinter as ctk
from tkinter import messagebox

APP_NAME = "sysZ"
XBOX_DNS_IP = "176.99.11.77"
CREATE_NO_WINDOW = 0x08000000

GITHUB_REPOS = {
    "roblox": "Lux1de/zapret-roblox",
    "flowseal": "Flowseal/zapret-discord-youtube"
}

BASE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Temp"), "sysZ_Launcher")

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

ICON_PATH = get_resource_path("icon.ico")

class SysZLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()
        if not self.is_admin(): self.run_as_admin()

        self.title(APP_NAME)
        self.geometry("500x650")
        self.resizable(False, False)
        
        if os.path.exists(ICON_PATH):
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"mycompany.{APP_NAME}.v1")
                self.iconbitmap(ICON_PATH)
            except: pass

        self.protocol('WM_DELETE_WINDOW', self.hide_window)
        self.running = False
        self.current_proc = None
        os.makedirs(BASE_DIR, exist_ok=True)
        self.setup_ui()
        self.create_tray()

    def is_admin(self):
        try: return ctypes.windll.shell32.IsUserAnAdmin()
        except: return False

    def run_as_admin(self):
        script = os.path.abspath(sys.argv[0])
        executable = sys.executable.replace("python.exe", "pythonw.exe")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, f'"{script}"', None, 1)
        sys.exit()

    def setup_ui(self):
        ctk.set_appearance_mode("dark")
        self.label = ctk.CTkLabel(self, text=APP_NAME, font=("Segoe UI", 36, "bold"), text_color="#3498db")
        self.label.pack(pady=25)

        ctk.CTkLabel(self, text="ВЫБОР DNS:").pack()
        self.dns_menu = ctk.CTkOptionMenu(self, values=[XBOX_DNS_IP, "1.1.1.1", "8.8.8.8"], fg_color="#2c3e50")
        self.dns_menu.set(XBOX_DNS_IP)
        self.dns_menu.pack(pady=10)

        ctk.CTkLabel(self, text="ПРОФИЛЬ ОБХОДА:").pack()
        self.mode_menu = ctk.CTkOptionMenu(self, values=[
            "General (Best)", "FAKE TLS AUTO", "SIMPLE FAKE", "ALT Speed Test", "Roblox Mode"
        ], fg_color="#2c3e50")
        self.mode_menu.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="СТАТУС: ГОТОВ", text_color="gray", font=("Consolas", 14))
        self.status_label.pack(pady=15)

        self.start_btn = ctk.CTkButton(self, text="ЗАПУСК", fg_color="#2ecc71", hover_color="#27ae60", 
                                      command=self.toggle_service, height=60, font=("Arial", 20, "bold"))
        self.start_btn.pack(pady=20, padx=60, fill="x")

        self.update_btn = ctk.CTkButton(self, text="ОБНОВИТЬ ФАЙЛЫ", command=self.check_updates, fg_color="#34495e")
        self.update_btn.pack(pady=10)

    def set_dns(self, dns_ip):
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            ps_cmd = 'Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object -ExpandProperty Name'
            output = subprocess.check_output(['powershell', '-Command', ps_cmd], startupinfo=si, creationflags=CREATE_NO_WINDOW).decode('cp866')
            adapters = [line.strip() for line in output.split('\n') if line.strip()]
            for adapter in adapters:
                subprocess.run(f'netsh interface ip set dns name="{adapter}" static {dns_ip} primary', 
                               shell=True, capture_output=True, startupinfo=si, creationflags=CREATE_NO_WINDOW)
        except: pass

    def check_updates(self):
        def task():
            self.update_btn.configure(state="disabled")
            headers = {'User-Agent': 'Mozilla/5.0'}
            try:
                for name, repo_path in GITHUB_REPOS.items():
                    self.status_label.configure(text=f"СКАЧИВАЕМ {name.upper()}...", text_color="yellow")
                    dl_url = f"https://github.com/{repo_path}/archive/refs/heads/main.zip"
                    zip_path = os.path.join(BASE_DIR, f"{name}.zip")
                    with requests.get(dl_url, headers=headers, stream=True, timeout=20) as dl:
                        dl.raise_for_status()
                        with open(zip_path, 'wb') as f:
                            for chunk in dl.iter_content(chunk_size=16384): f.write(chunk)
                    target_extract = os.path.join(BASE_DIR, name)
                    if os.path.exists(target_extract): shutil.rmtree(target_extract, ignore_errors=True)
                    with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(target_extract)
                    if os.path.exists(zip_path): os.remove(zip_path)
                self.status_label.configure(text="ФАЙЛЫ ГОТОВЫ", text_color="green")
            except Exception as e: messagebox.showerror("Ошибка", str(e))
            finally: self.update_btn.configure(state="normal")
        threading.Thread(target=task, daemon=True).start()

    def toggle_service(self):
        if not self.running: self.start_service()
        else: self.stop_service()

    def start_service(self):
        self.set_dns(self.dns_menu.get())
        bat_map = {
            "General (Best)": "general.bat",
            "FAKE TLS AUTO": "general (FAKE TLS AUTO).bat",
            "SIMPLE FAKE": "general (SIMPLE FAKE).bat",
            "ALT Speed Test": "general (ALT).bat",
            "Roblox Mode": "discord_youtube.bat"
        }
        target_bat = bat_map.get(self.mode_menu.get(), "general.bat")
        found_bat = None
        for root, _, files in os.walk(BASE_DIR):
            if target_bat in files:
                found_bat = os.path.join(root, target_bat)
                break
        if not found_bat:
            messagebox.showerror("Ошибка", "Файлы не найдены. Нажми ОБНОВИТЬ.")
            return
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            self.current_proc = subprocess.Popen(
                ["cmd", "/c", found_bat], 
                cwd=os.path.dirname(found_bat),
                startupinfo=si,
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.running = True
            self.start_btn.configure(text="ОСТАНОВИТЬ", fg_color="#e74c3c")
            self.status_label.configure(text="РАБОТАЕТ", text_color="#2ecc71")
        except Exception as e: messagebox.showerror("Ошибка", str(e))

    def stop_service(self):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        subprocess.run("taskkill /F /IM winws.exe /T", shell=True, capture_output=True, startupinfo=si, creationflags=CREATE_NO_WINDOW)
        if self.current_proc: self.current_proc.terminate()
        self.running = False
        self.start_btn.configure(text="ЗАПУСК", fg_color="#2ecc71")
        self.status_label.configure(text="ОСТАНОВЛЕН", text_color="gray")

    def create_tray(self):
        img = Image.open(ICON_PATH) if os.path.exists(ICON_PATH) else Image.new('RGB', (64, 64), (52, 152, 219))
        menu = pystray.Menu(pystray.MenuItem("Показать", self.show_window), pystray.MenuItem("Выход", self.quit_app))
        self.tray = pystray.Icon(APP_NAME, img, APP_NAME, menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def hide_window(self): self.withdraw()
    def show_window(self): self.deiconify()

    def quit_app(self, icon=None, item=None):
        self.stop_service()
        if hasattr(self, 'tray'): self.tray.stop()
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = SysZLauncher()
    app.mainloop()