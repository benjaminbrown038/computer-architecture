; Task: compute 5 + 4 + 3 + 2 + 1.
MOV R0, 0
MOV R1, 5
loop:
ADD R0, R1
DEC R1
JNZ R1, loop
STORE R0, 16
HALT
