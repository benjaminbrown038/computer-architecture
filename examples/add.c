/* The task expressed in C. This is separate from the toy CPU interpreter. */
#include <stdio.h>
int add(int a, int b) { return a + b; }
int main(void) { printf("%d\n", add(5, 7)); return 0; }
