; Two work orders using one routine. R0 returns each estimate.
; CALL saves the following instruction index; RET resumes there.
; Expected memory[16]=47, memory[17]=20, memory[18]=67.
; Whole minutes, fixed cycle times; totals must fit in 0..255.
; Zero quantity still includes setup time.
MOV R0, 12
MOV R1, 7
MOV R2, 5
CALL estimate
STORE R0, 16
MOV R0, 8
MOV R1, 4
MOV R2, 3
CALL estimate
STORE R0, 17
LOAD R0, 16
LOAD R1, 17
ADD R0, R1
STORE R0, 18
HALT
estimate:
JNZ R2, add_part
RET
add_part:
ADD R0, R1
DEC R2
JNZ R2, add_part
RET
