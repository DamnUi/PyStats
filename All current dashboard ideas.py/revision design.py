from rich.console import Group
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.align import Align    
from rich.layout import Layout
from rich.live import Live
from datetime import datetime
from rich.progress import ProgressColumn, ProgressBar, Progress

console = Console(height=5) #possibly some kind of external algorithm to find an appropriate size and length?

maintitle_markdown = f"""
# PyStats {datetime.time(datetime.now())}
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
def make_bar(size_1=50, size_2=85):
    layout = Layout()

    layout.split_column(
        Layout(name="lower", ratio=5)
    )


    layout["lower"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )

    layout["lower"]["left"].size = size_1
    layout['lower']['right'].size = size_2 
    
    return layout['lower']

bar1 = make_bar()
bar2 = make_bar()
bar3 = make_bar()

unwrap = Group(
    Markdown('Text', style='red', justify='center')
    
    
)




bar1['left'].update(Panel(unwrap, style='blue'))
    
console.print(wraped_less_stats, bar1, bar2, bar3)