import time

def find_indices(line, target):
    index1 = 0

    valid_front, valid_back = False, False
    while True:
        next_index = line[index1:].find(target)
        if next_index < 0:      # target not in string
            return -1, -1
        index1 += next_index    # jump to head of found target
        
        valid_front = index1 == 0
        if index1 > 0:                              # if there are characters in front of target
            valid_front = line[index1 - 1] in ", "  # other characters like [a-z][0-9][_$#*] etc. not allowed
        
        index1 += len(target)   # jump to tail of found target: doesn't repeatedly find the same word
        valid_back = index1 == len(line)
        if index1 < len(line):        # if there are characters behind target
            valid_back = line[index1] in ":= "
        
        print(valid_front, valid_back)
        time.sleep(0.25)
        
        if valid_front and valid_back:
            break
            
    while line[index1] in " =:": # move forward until at start of assignment
        index1 += 1

    if '"' in line[index1:]:    # if var assignment is a string, ignore symbols
        index2 = line[index1:].find('"') + index1 + 1
        index2 = line[index2:].find('"') + index2
        return index1, index2
        
    if "'" in line[index1:]:    # if var assignment is a string, ignore symbols
        index2 = line[index1:].find("'") + index1 + 1
        index2 = line[index2:].find("'") + index2
        return index1, index2

    index2 = len(line) - 1  # initialize at end of line
    for c in "} ,":  # value ends in ,/ /} whichever is smallest but must > -1
        index_temp = line[index1:].find(c) + index1
        index2 = index_temp if index_temp > -1 + index1 and index_temp < index2 else index2
    return index1, index2
           
test_strings = ["docker = 'x'",
                "mound = sand, docker = 3",
                "okay, docker: ~{3}",
                "docker1 = 'no', docker2 = 'no', docker = 'yes', docker4 = 'no'",
                "xdocker = 'x'",
                "dockerx = 'x'",
                "_docker_: 3"]
           
for line in test_strings:
    target = "docker"
    index1, index2 = find_indices(line, target)
    print(index1, index2)
    print(line + " /// " + line[index1:index2 + 1])
    
# put items after, similar dockers on same line
    
    
    
    