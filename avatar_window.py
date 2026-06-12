#!/usr/bin/env python3

import sys
import webview

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5577"

    webview.create_window(
        "My AI — Avatar",
        url,
        width=420,
        height=640,
        on_top=True,
        transparent=False,
        frameless=False,
    )

    # Paksa Qt
    webview.start(gui="qt", debug=True)

if __name__ == "__main__":
    main()
    