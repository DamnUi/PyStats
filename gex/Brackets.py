import re

pattern = r"[(|)].*"
test_string = "Hello (World))))(!"
# selects (World))))(! so it should remove it, courtesy of https://regex101.com/


gex = re.sub(pattern, "", test_string) #removes all selected txt from string

print(gex)







