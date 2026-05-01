import argparse
import subprocess
import sys

from cobrain.html.html import build_html


def cmd_show(args: argparse.Namespace) -> None:
    graph_path = build_html()
    print(f"Vault page ready: {graph_path}")

    _open_browser(str(graph_path))


def _open_browser(path: str) -> None:
    platform = sys.platform

    try:
        if platform == "darwin":
            subprocess.run(["open", path], check=True)
        elif platform == "win32":
            subprocess.run(["start", "", path], shell=True, check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)
    except Exception:
        print(f"Open in browser: {path}")
