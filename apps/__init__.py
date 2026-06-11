# Placeholder for app registry
import importlib
import os

def run_app(app_name):
    try:
        # Mencoba memuat modul aplikasi secara dinamis
        app_module = importlib.import_module(f"my_ai_cli.apps.{app_name}")
        if hasattr(app_module, 'run'):
            app_module.run()
        else:
            print(f"App '{app_name}' tidak memiliki fungsi run().")
    except ImportError:
        print(f"App '{app_name}' tidak ditemukan.")

def list_apps():
    apps_dir = os.path.dirname(__file__)
    return [f for f in os.listdir(apps_dir) if f.endswith('.py') and f != '__init__.py']
