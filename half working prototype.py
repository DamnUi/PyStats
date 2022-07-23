import inspect
from pathlib import Path
import os
from rich.console import Console
from rich.traceback import install as install_traceback
from rich import print, pretty
import time
from rich.panel import Panel
#Usage: print(Panel.fit("Hello, [red]World!", title="Welcome", subtitle="Thank you"))
pretty.install()
install_traceback(show_locals=True)



class imports():
    def __init__(self, overide=None):
            if overide:
                self.file_called = overide
            else:
                self.file_called = Path(inspect.stack()[1].filename)
            
            self.imports_ = [f'#Fine path called {self.file_called}',
                'from rich.console import Console',
                        'from rich.traceback import install as install_traceback',
                        'from rich import print, pretty',
                        'import time',
                        'from rich.panel import Panel',
                        '#Usage: print(Panel.fit("Hello, [red]World!", title="Welcome", subtitle="Thank you"))',
                        'pretty.install()',
                        'install_traceback(show_locals=True)',
                        ]
    
    def path(self):
        return self.file_called
    

    
    def write_to_file(self):
        with open(self.file_called, 'w', encoding='utf8') as f:
            for line in self.imports_:
                f.write(line + '\n')
        return self.file_called

def immiimport():
    
    imports(Path(inspect.stack()[1].filename)).write_to_file()
    
class learn:
    def __init__(self, bypass=None) -> None:
        if bypass:
            self.called_path = bypass
        else:
            self.called_path = Path(inspect.stack()[1].filename)
        
        
    def scrape_imports(self):
        lines = [line.strip() for line in open(self.called_path, encoding='utf8')]
        imports_ = []
        for line in lines:
            if line.startswith('import'):
                imports_.append(line)
            elif line.startswith('from'):
                imports_.append(line)
        return imports_
   
    def get_import_names(self):
        imports_ = self.scrape_imports()
        import_names = []
        for line in imports_:
            #Split from space
            line_split = line.split()
            #Get the second word
            try:
                import_names.append(line_split[1])
            except IndexError:
                pass
        return(import_names)
              
            
    def refine_imports(self):
        all_imports = self.scrape_imports()
        imports_ = []
        for line in all_imports:
                #if the line is more then 4 words discard it, if it has commas then increase the word count by the number of commas
            if len(line.split()) > 4:  
                continue
            elif ',' in line:
                word_count = len(line.split()) + len(line.split(','))
            else:
                word_count = len(line.split())
            if word_count > 4:
                continue
            else:
                imports_.append(line)
        return imports_

    def writen(self, file_name):
        file_path = file_name + '.txt'
        with open(file_path, 'a', encoding='utf8') as f:
            f.write('From ' + self.called_path + '\n')
            for line in self.scrape_imports():
                f.write(line + '\n')
        return file_path
    
    
    


#Might need to redo the enitre project here is the basic idea
#Command line utility to find which modules you use the most: 
#pklib -d <directory> -o <output file> -exc <exclude file>
#Reads the entire dictionary and selects the python files reads the imports in them and writes stats/ most used in them


class main:
    def __init__(self, dir='.Zdiscord') -> None:
        self.called_path = Path(inspect.stack()[1].filename)
        self.lines = [line.strip() for line in open(self.called_path, encoding='utf8')]
        self.directory = dir

    def get_files(self, directory):
        #Full path of all files in the directory
        paths = []
        for dirpath,_,filenames in os.walk(directory):
            for f in filenames:
                paths.append(os.path.abspath(os.path.join(dirpath, f)))
        return paths
        
    
    def import_data(self):
        diction = {}
        files = self.get_files(self.directory)
        for file in files:
            diction[file] = learn(file).get_import_names()
        return diction
    
    def get_most_used(self):
        diction = self.import_data()
        most_used = {}  
        for file in diction:
            for import_ in diction[file]:
                if import_ in most_used:
                    most_used[import_] += 1
                else:
                    most_used[import_] = 1
        #Arrange is in descending order
        most_used = sorted(most_used.items(), key=lambda x: x[1], reverse=True)
        return most_used
                    
    def main(self):
        stuff = self.get_most_used()
        with open( 'most_used.txt', 'w', encoding='utf8') as f:
            for line in stuff:
                f.write(str(line) + '\n')
            
        
    
    
    
print(main(dir=r'D:\1.Autohotkey\.Python\Project Folders\AAnimate.py').main())  

















 