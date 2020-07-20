def find_indices(line, target):
    index1 = line.find(target)

    valid_front, valid_back = False, False
    while not valid_front or not valid_back:
        next_index = line[index1:].find(target)
        if next_index < 0:  # target not in string
            return -1, -1
        index1 += next_index
        valid_front = index1 == 0
        if index1 > 0:                              # if there are characters in front of target
            valid_front = line[index1 - 1] in ", "  # other characters like [a-z][0-9][_$#*] etc. not allowed
        valid_back = index1 + len(target) == len(line)
        if index1 + len(target) < len(line):        # if there are characters behind target
            valid_back = line[index1 + 1] in ":= "
            
    index1 +=  len(target)      # skip to where the assignment starts
    print(index1)
    while line[index1] in " =": # move forward until at start of assignment
        index1 += 1

    if '"' in line[index1:]:    # if var assignment is a string, ignore symbols
        index2 = line[index1:].find('"') + index1 + 1
        index2 = line[index2:].find('"') + index2 + 1
        return index1, index2

    index2 = len(line) - 1  # initialize at end of line
    for c in "} ,":  # value ends in ,/ /} whichever is smallest but must > -1
        index_temp = line[index1:].find(c) + index1
        index2 = index_temp if index_temp > index1 - 1 and index_temp < index2 else index2
    return index1, index2
            
while True:
    line = input("line: ")
    target = input("target: ")
    index1, index2 = find_indices(line, target)
    print(index1, index2)
    print(line[index1:index2])