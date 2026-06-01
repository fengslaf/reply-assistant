#!/usr/bin/env python3
"""Diagnostic entry point - captures all errors to file."""

import sys
import os
import traceback
from pathlib import Path

def get_error_log_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / 'error_log.txt'
    return Path(__file__).parent / 'error_log.txt'

def main():
    error_log = get_error_log_path()
    
    try:
        from start_gui import main as gui_main
        gui_main()
    except Exception as e:
        with open(error_log, 'w', encoding='utf-8') as f:
            f.write(f"Error Type: {type(e).__name__}\n")
            f.write(f"Error Message: {str(e)}\n\n")
            f.write("Full Traceback:\n")
            traceback.print_exc(file=f)
            f.write("\n\n=== Environment Info ===\n")
            f.write(f"sys.executable: {sys.executable}\n")
            f.write(f"sys.frozen: {getattr(sys, 'frozen', False)}\n")
            f.write(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}\n")
            f.write(f"TCL_LIBRARY: {os.environ.get('TCL_LIBRARY', 'NOT SET')}\n")
            f.write(f"TK_LIBRARY: {os.environ.get('TK_LIBRARY', 'NOT SET')}\n")
            f.write(f"\nsys.path:\n")
            for p in sys.path:
                f.write(f"  {p}\n")
        print(f"Error logged to: {error_log}")
        raise

if __name__ == '__main__':
    main()