
from rich.console import Group
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
from rich.text import Text

hwnd = win32gui.GetForegroundWindow()
win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

md = f"""
# Title
"""

more_text = """


"""


md_2 = """
# Title
"""

main_title = """
# PyStats
"""
    
console = Console(height=15, width=160)

layout = Layout()

layout.split_column(
    Layout(name="lower", ratio=5)
)


layout["lower"].split_row(
    Layout(name="left"),
    Layout(name="right"),
)

layout["lower"]["left"].size = 50

panel_group = Group(
    Markdown(md),
    Align(Panel('[red]Okay', border_style='blue'), align='left') 
    
    
) 

layout["lower"]["right"].update(Panel(panel_group,  border_style='blue', style='green'))


#num 73 might change
#layout["lower"]["right"].update(Panel(Align(Panel(md, box=box.DOUBLE, padding=(0, 73)), align='center'), border_style='blue', style='green'))
layout["lower"]["left"].update(Panel(Markdown(md_2), border_style='blue', style='magenta'))

print(layout)
