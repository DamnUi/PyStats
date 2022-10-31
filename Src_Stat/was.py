import ast

#scrape _PyStats.py for variables and get its type
with open('tses.py', 'r') as f:
    tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                print(target.id, type(node.value).__name__)