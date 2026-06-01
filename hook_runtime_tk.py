#!/usr/bin/env python3
"""Runtime hook for TCL/TK in PyInstaller onefile mode."""

import sys
import os

def setup_tcl_tk():
    if getattr(sys, 'frozen', False):
        meipass = sys._MEIPASS
        
        tcl_names = ['tcl8.6', '_tcl_data', 'tcl', 'tcl_data']
        tk_names = ['tk8.6', '_tk_data', 'tk', 'tk_data']
        
        tcl_dir = None
        tk_dir = None
        
        for name in tcl_names:
            path = os.path.join(meipass, name)
            if os.path.isdir(path):
                tcl_dir = path
                break
        
        for name in tk_names:
            path = os.path.join(meipass, name)
            if os.path.isdir(path):
                tk_dir = path
                break
        
        if tcl_dir:
            os.environ['TCL_LIBRARY'] = tcl_dir
        if tk_dir:
            os.environ['TK_LIBRARY'] = tk_dir
        
        icon_path = os.path.join(meipass, 'app.ico')
        if os.path.exists(icon_path):
            os.environ['APP_ICON_PATH'] = icon_path

setup_tcl_tk()