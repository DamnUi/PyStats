import ast
#print(n.targets[0].ctx, n.targets[00]._fields)
with open('PyStats.py', encoding='utf-8') as f:
    code = f.read()
    
    node = ast.parse(code)
    scrp_var = 0

    if_list = []
    while_list = []
    for_or_aysync_for_list = []
    with_list = []

    
    for thing in ast.walk(node=node):
        if isinstance(thing, ast.If):
            if_list.append(thing)
        
        
    #Find a count of all if statments in the file 
    # for indx, obj in enumerate(list(node.body)):
    #     if isinstance(obj, ast.ClassDef):
    #         for indx, new in enumerate(list(obj.body)):
    #             if isinstance(new, ast.FunctionDef):
    #                 for indx, new in enumerate(list(new.body)):
    #                     if isinstance(new, ast.If):
    #                         if_list.append(new)



print(len(if_list))
#print all the lists 


            
    
                        

                        
            


                
        
        
        
        




        
        
                

        
    
    