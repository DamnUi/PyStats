from rich.console import Group
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.align import Align    
from rich.layout import Layout

console = Console(height=5) #possibly some kind of external algorithm to find an appropriate size and length?

maintitle_markdown = f"""
# PyStats
"""



unwraped_main_screen = Group(
   Markdown(maintitle_markdown,
             style='yellow', #Text Style
             )   
    )
    
wraped_main_screen = Align(unwraped_main_screen, align='center', style='green')#Can Change border style here by changing style



stat_less_md = f"""
File Path(s):? , Pc_Name: not needed , User: not needed , Date: , Time_to_file_report: possibly not needed
could also add info about varibles and imports here?
"""

unwraped_less_stats = Group(
    Panel(Markdown(stat_less_md,
                style='yellow', #Text Style
                )
    ))
#panel


wraped_less_stats = Align(Panel(stat_less_md, title='Quickies', title_align='left', width=91), align='left', style='black')#Can Change border style here by changing style

#Now for the real main screen
layout = Layout()

layout.split_column(
    Layout(name="lower", ratio=5)
)


layout["lower"].split_row(
    Layout(name="left"),
    Layout(name="right"),
)

layout["lower"]["left"].size = 50



console.print(wraped_main_screen, wraped_less_stats, layout)
