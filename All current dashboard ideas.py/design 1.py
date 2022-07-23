
import time
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.align import Align
from rich.table import Table
from rich import print
from rich.layout import Layout
import win32gui, win32con

hwnd = win32gui.GetForegroundWindow()
win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

md = """
# Title
"""
md_2 = """
# Title
"""

main_title = """
# Okay
"""
    
console = Console(height=15, width=160)

layout = Layout()

layout.split_column(
    Layout(name="lower")
)


layout["lower"].split_row(
    Layout(name="left"),
    Layout(name="right"),
)
layout["lower"]["left"].size = 50

layout["lower"]["right"].update(Panel(Markdown(md), border_style='blue', style='green'))

layout["lower"]["left"].update(Panel(Markdown(md_2), border_style='blue', style='magenta'))


print(Panel(Markdown(main_title), border_style='blue', style='green'))
print()