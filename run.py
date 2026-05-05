#!/usr/bin/env python3
"""
Запуск AI Video Studio с Cloudflare Tunnel
"""
import subprocess
import time
import sys
import os
import threading

def main():
    # Переключаемся в каталог проекта
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Добавляем project_dir в sys.path для импортов
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    print("🚀 Запуск AI Video Studio...")
    print(f"   Каталог: {project_dir}")
    print("   Доступно на http://127.0.0.1:8000")

    # Запускаем сервер
    server = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "src.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload",
        "--no-access-log",
        "--log-level", "warning"
    ])

    # Ждём запуска сервера
    time.sleep(4)

    # Запускаем cloudflared в отдельном потоке
    def run_cloudflared():
        try:
            tunnel = subprocess.Popen([
                "cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"
            ])
            tunnel.wait()
        except Exception as e:
            print(f"   ❌ Cloudflared error: {e}")

    cloudflared_thread = threading.Thread(target=run_cloudflared, daemon=True)
    cloudflared_thread.start()
    print("   🌍 Cloudflare Tunnel запущен")

    # Ждём завершения сервера
    try:
        server.wait()
    except KeyboardInterrupt:
        print("\n🛑 Остановка...")
        server.terminate()
        time.sleep(1)

if __name__ == "__main__":
    main()
