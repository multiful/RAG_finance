import os
import sys
from pathlib import Path

# Ensure we can import from 'app'
# This script should be in app/backend/scripts/list_routes.py
# The 'app' package is in app/backend/app/
current_file = Path(__file__).resolve()
backend_root = current_file.parent.parent
sys.path.append(str(backend_root))

# Set dummy env vars for initialization if missing
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")

try:
    from app.main import app
    from fastapi.routing import APIRoute

    def list_routes():
        routes = []
        for route in app.routes:
            if isinstance(route, APIRoute):
                routes.append({
                    "path": route.path,
                    "methods": sorted(list(route.methods))
                })
        
        # Sort by path
        routes.sort(key=lambda x: x["path"])
        
        print(f"{'Path':<60} {'Methods'}")
        print("-" * 80)
        for r in routes:
            print(f"{r['path']:<60} {r['methods']}")

    if __name__ == "__main__":
        list_routes()
except ImportError as e:
    print(f"Import Error: {e}")
    print(f"Current sys.path: {sys.path}")
except Exception as e:
    print(f"An error occurred: {e}")
