; Work-order time estimator for the archlab teaching CPU.
; Run from the repository root:
; python3 -m archlab.cpu programs/work-order-time.asm --trace
;
; Example: 12 setup minutes + 5 parts * 7 minutes/part = 47 minutes.
; Inputs: memory[20] = setup minutes, [21] = minutes per part,
;         memory[22] = quantity. Output: memory[16] = total minutes.
; Scope: whole numbers 0..255; total must be <=255 to avoid wraparound.
; Fixed cycle time; excludes downtime and overlapping operations.
; Setup is included even for zero parts.

; Enter inputs. MOV places a number in R3; STORE copies it to memory.
MOV R3, 12
STORE R3, 20
MOV R3, 7
STORE R3, 21
MOV R3, 5
STORE R3, 22

; R0 holds elapsed minutes, R1 holds minutes per part,
; and R2 holds the number of parts remaining.
LOAD R0, 20
LOAD R1, 21
LOAD R2, 22

; Skip the loop for a zero-quantity job.
; JNZ jumps only if its register is nonzero.
JNZ R2, make_part
STORE R0, 16
HALT

make_part:
ADD R0, R1
DEC R2
JNZ R2, make_part

; Store the completed estimate and stop.
STORE R0, 16
HALT
