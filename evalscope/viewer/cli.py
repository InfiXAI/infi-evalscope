"""
Viewer CLI

Command line interface for the EvalScope Viewer.
"""

import argparse
import atexit
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Global variable to track frontend process
_frontend_process: Optional[subprocess.Popen] = None


def cmd_sync(args):
    """Sync cache from outputs directory"""
    from evalscope.viewer.storage import get_storage

    outputs_dir = Path(args.outputs_dir)
    if not outputs_dir.exists():
        print(f"Error: Directory not found: {outputs_dir}")
        sys.exit(1)

    print(f"Syncing from {outputs_dir}...")
    storage = get_storage(
        mode=args.mode,
        outputs_dir=str(outputs_dir),
        data_dir=args.data_dir,
    )

    new_count = storage.sync(str(outputs_dir))
    total = len(storage.get_cached_run_ids())

    print(f"Sync complete: {new_count} new runs cached, {total} total runs")


def _cleanup_frontend():
    """Cleanup frontend process on exit"""
    global _frontend_process
    if _frontend_process is not None:
        print("\nStopping frontend server...")
        try:
            _frontend_process.terminate()
            _frontend_process.wait(timeout=5)
        except Exception:
            _frontend_process.kill()
        _frontend_process = None


def _start_frontend(frontend_dir: Path, frontend_port: int, api_port: int) -> bool:
    """Start the frontend dev server"""
    global _frontend_process

    if not frontend_dir.exists():
        print(f"  Warning: Frontend directory not found: {frontend_dir}")
        return False

    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        print(f"  Warning: package.json not found in {frontend_dir}")
        return False

    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("  Installing frontend dependencies...")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"  Warning: Failed to install dependencies: {e}")
            return False
        except FileNotFoundError:
            print("  Warning: npm not found. Please install Node.js.")
            return False

    # Set environment variables for the frontend
    env = os.environ.copy()
    env["PORT"] = str(frontend_port)
    env["NEXT_PUBLIC_API_URL"] = f"http://127.0.0.1:{api_port}"

    try:
        _frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Register cleanup
        atexit.register(_cleanup_frontend)
        return True
    except FileNotFoundError:
        print("  Warning: npm not found. Please install Node.js.")
        return False
    except Exception as e:
        print(f"  Warning: Failed to start frontend: {e}")
        return False


def cmd_serve(args):
    """Start the viewer server"""
    global _frontend_process

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required. Install with: pip install uvicorn")
        sys.exit(1)

    outputs_dir = Path(args.outputs_dir)
    if not outputs_dir.exists():
        print(f"Error: Outputs directory not found: {outputs_dir}")
        sys.exit(1)

    # Sync on startup
    print(f"Syncing from {outputs_dir}...")
    from evalscope.viewer.storage import get_storage

    storage = get_storage(
        mode=args.mode,
        outputs_dir=str(outputs_dir),
        data_dir=args.data_dir,
    )
    new_count = storage.sync(str(outputs_dir))
    total = len(storage.get_cached_run_ids())
    print(f"  Found {total} runs ({new_count} new)")
    print()

    # Start frontend if requested
    if args.with_web:
        viewer_dir = Path(__file__).parent
        frontend_dir = viewer_dir / "web"

        print("Starting frontend server...")
        if _start_frontend(frontend_dir, args.frontend_port, args.port):
            print(f"  Frontend: http://127.0.0.1:{args.frontend_port}")
        else:
            print("  Frontend server not started (continuing with API only)")
        print()

    print("Starting EvalScope Viewer server...")
    print(f"  Mode: {args.mode}")
    print(f"  Outputs: {outputs_dir}")
    print(f"  Data: {args.data_dir}")
    print(f"  API: http://{args.host}:{args.port}")
    if args.with_web:
        print(f"  Frontend: http://127.0.0.1:{args.frontend_port}")
    print()

    from evalscope.viewer.server import create_app

    app = create_app(
        mode=args.mode,
        outputs_dir=str(outputs_dir),
        data_dir=args.data_dir,
    )

    try:
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        _cleanup_frontend()


def cmd_list(args):
    """List all runs in storage"""
    from evalscope.viewer.storage import get_storage

    storage = get_storage(
        mode=args.mode,
        outputs_dir=args.outputs_dir,
        data_dir=args.data_dir,
    )

    # Sync first if outputs_dir exists
    outputs_dir = Path(args.outputs_dir)
    if outputs_dir.exists():
        storage.sync(str(outputs_dir))

    runs, total = storage.list_runs(limit=args.limit, offset=0)

    if not runs:
        print("No runs found.")
        return

    print(f"Found {total} run(s):\n")
    for run in runs:
        score = run.get("overall_score", 0)
        score_str = f"{score * 100:.1f}%" if score else "N/A"
        model_name = run.get("model_name", "Unknown")
        datasets = ", ".join(run.get("datasets", []))

        print(f"  {run['run_id']}")
        print(f"    Model: {model_name}")
        print(f"    Score: {score_str}")
        print(f"    Datasets: {datasets}")
        print(f"    Status: {run.get('status', 'unknown')}")
        print()


def cmd_delete(args):
    """Delete a run from storage"""
    from evalscope.viewer.storage import get_storage

    storage = get_storage(
        mode=args.mode,
        outputs_dir=args.outputs_dir,
        data_dir=args.data_dir,
    )

    if not storage.run_exists(args.run_id):
        print(f"Error: Run not found: {args.run_id}")
        sys.exit(1)

    if not args.force:
        confirm = input(f"Delete run {args.run_id}? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return

    success = storage.delete_run(args.run_id)
    if success:
        print(f"Deleted: {args.run_id}")
    else:
        print(f"Failed to delete: {args.run_id}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="evalscope-viewer",
        description="EvalScope Viewer - Visualization for evaluation results",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Common arguments
    def add_common_args(p):
        p.add_argument(
            "--mode",
            choices=["single", "team"],
            default="single",
            help="Storage mode (default: single)",
        )
        p.add_argument(
            "--outputs-dir",
            default="./outputs",
            help="EvalScope outputs directory (default: ./outputs)",
        )
        p.add_argument(
            "--data-dir",
            default=".viewer",
            help="Viewer data directory (default: .viewer)",
        )

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync cache from outputs directory")
    add_common_args(sync_parser)
    sync_parser.set_defaults(func=cmd_sync)

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start viewer server")
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=7862,
        help="API server port (default: 7862)",
    )
    serve_parser.add_argument(
        "--with-web",
        action="store_true",
        help="Also start the web frontend server",
    )
    serve_parser.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Frontend server port (default: 3000)",
    )
    add_common_args(serve_parser)
    serve_parser.set_defaults(func=cmd_serve)

    # list command
    list_parser = subparsers.add_parser("list", help="List all runs")
    list_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum runs to list (default: 100)",
    )
    add_common_args(list_parser)
    list_parser.set_defaults(func=cmd_list)

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a run")
    delete_parser.add_argument("run_id", help="Run ID to delete")
    delete_parser.add_argument(
        "-f", "--force", action="store_true", help="Skip confirmation"
    )
    add_common_args(delete_parser)
    delete_parser.set_defaults(func=cmd_delete)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
