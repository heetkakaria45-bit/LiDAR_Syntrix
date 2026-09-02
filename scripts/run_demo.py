"""One-Command Interactive Demo Launcher for Autonomous Perception Control Center.

Usage:
    python3 scripts/run_demo.py [--port 8080] [--headless]
"""

import argparse
from pathlib import Path
import sys
import webbrowser

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.integration.pipeline import PipelineMode, PipelineOrchestrator
from src.visualization.dashboard import print_terminal_dashboard
from src.visualization.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="SYNTRiX // Autonomous Perception Demo")
    parser.add_argument("--port", type=int, default=8080, help="Web server port (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web server host (default: 127.0.0.1)")
    parser.add_argument("--headless", action="store_true", help="Run console telemetry without web UI")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    orchestrator = PipelineOrchestrator(mode=PipelineMode.SYNTHETIC)

    if args.headless:
        print_terminal_dashboard(orchestrator, max_frames=10)
        return

    server = run_server(port=args.port, host=args.host, orchestrator=orchestrator)
    url = f"http://{args.host}:{args.port}"
    print(f"Opening web visualizer at: {url}")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    main()
