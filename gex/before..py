import re

pattern = r"(([^\.])+\.+)+"
test_string = 'anything.here.will.be.remove.only.the.text.after.this.will.be.kept'
# selects anything.here.will.be.remove.only.the.text.after.this.will.be. so it should remove it, courtesy of https://regex101.com/, useful for self. expressions and in finding varibles and functions


gex = re.sub(pattern, "", test_string) #removes all selected txt from string

print(gex)  

