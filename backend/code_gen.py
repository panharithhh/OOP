import random

def gen_pass():
    
    ran_pass = []
    
    
    for i in range(0,6):
        ran_num = random.randint(0,9)
        ran_pass.append((ran_num)) 
    
    ran_pass_as_str =[]
    for num in ran_pass:
        ran_pass_as_str.append(str(num))
        
    final_ran_pass = "".join(ran_pass_as_str)
        

    return final_ran_pass
    
    
