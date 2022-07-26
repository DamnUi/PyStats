import argparse
import os
import pathlib
from collections import Counter 
import re


#Dashboard imports
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.align import Align
import os

#Fine path called d:\1.Autohotkey\.Python\Project Folders\portswwww.py
from rich.console import Console
from rich.traceback import install as install_traceback
from rich import print, pretty
import time
from rich.panel import Panel
#Usage: print(Panel.fit("Hello, [red]World!", title="Welcome", subtitle="Thank you"))
pretty.install()
install_traceback(show_locals=False)
#Dashboard imports \\ or pretty imports?

# Initializing Parser

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-df", help="Input Absolute Path to Directory or File")
    #df is directory or file it will kinda figure out byitself assuming theirs only 2 files in the dir and u do -neglect
    parser.add_argument('-onefile', help="Input Absolute Path to File to Analyze")
    parser.add_argument("-neglect", help="Input Absolute Path to File to Ignore ONLY IN DIRECTORY") 
    #Debug argument to print out the file names
    path = parser.parse_args()
    #2 Varibles 
    #path.df
    #path.onefile ignores everything and makes sure u have just onefile ur scanning
    #Path.neglect
    
    if path.onefile:
        paths = [path.onefile]
    else:
        #Determine if its a directory or file
        if os.path.isdir(path.df):
            #If its a directory get all absolute paths of files in it ending with py
            paths = []
            for dirpath,_,filenames in os.walk(path.df):
                for f in filenames:
                    if f.endswith('.py'):
                        paths.append(os.path.abspath(os.path.join(dirpath, f)))
            #remove neglect from paths
            if path.neglect is not None:
                for line in paths:
                    original_line = line
                    line = line.replace("\\","/")
                    if path.neglect in line:
                        paths.remove(original_line)
        else:
            paths = [path.df]
    #That ends classification of the file
    
    
    
class Stat:
    def __init__(self, directory) -> None:
        self.directory = directory
        #Add .py to directory if not there
        if not self.directory[-1].endswith('.py'):
            self.directory[-1] += '.py'
        #Check if file exists
        if not os.path.exists(self.directory[-1]):
            print("[red]File does not exist")
            exit()
        #The Neglect keyword aint needed cause its already delt in the if statment from before 
        
    def scrape_imports(self):
        imports_ = []
        real_imports = []
        if len(self.directory) > 1:
            print("[green]Scraping imports from multiple files...")
            for path in self.directory:
                with open(path, encoding='utf8') as f:
                    for line in f:
                        if line.startswith('import'):
                            imports_.append(line)   
                        elif line.startswith('from'):
                            imports_.append(line)
        else:
            print("[green]Scraping imports from single file...")
            with open(self.directory[0], encoding='utf8') as f:
                for line in f:
                    if line.startswith('import'):
                        imports_.append(line)
                    elif line.startswith('from'):
                        imports_.append(line)
        
        for line in imports_:
            real_imports.append(line.strip())
        
        return real_imports
    
    def line_count(self):
        #if its a directory return the lines in a dict with the file name as the key
        if len(self.directory) > 1:
            line_count = {}
            for path in self.directory:
                with open(path, encoding='utf8') as f:
                    line_count[path] = len(f.readlines())
        else:
            with open(self.directory[0], encoding='utf8') as f:
                line_count = len(f.readlines())
        
        return line_count
    
    def most_used_varible(self):
        varibles = self.scrape_varibles()
        varible_count = Counter(varibles)
        dictionaryy = {}
        for key, value in varible_count.items():
            dictionaryy[key] = value
        most_used_varible = max(dictionaryy, key=dictionaryy.get)
        return most_used_varible, dictionaryy[most_used_varible]
        
        
    def scrape_varibles(self, full_line_of_varible=False):
        varibles = []
        var = {}
        with open(self.directory[0], encoding='utf8') as f:
            for line in f:
                if ' = ' in line:
                    if full_line_of_varible:
                        varibles.append(line)
                    varibles.append(line.split()[0])
                        
        return varibles


    def get_import_names(self):
        imports = self.scrape_imports()
        import_names = []
        for line in imports:
            if line.startswith('import'):
                import_names.append(line.split()[1])
            elif line.startswith('from'):
                import_names.append(line.split()[3])
                
        return import_names
                

            
info = Stat(paths)    
        
    
print(info.line_count(),
      info.most_used_varible(),
      info.scrape_varibles())
