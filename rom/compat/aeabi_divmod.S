// Adapted from LLVM compiler-rt release_32 lib/arm/aeabi_{l,ul}divmod.S.
// The original sources are dual licensed under MIT and University of Illinois
// Open Source licenses; see LICENSE.TXT in this directory.
// ARM EABI returns quotient in r0:r1 and remainder in r2:r3.

    .syntax unified
    .arm
    .text
    .align 2
    .global __aeabi_ldivmod
    .type __aeabi_ldivmod, %function
__aeabi_ldivmod:
    push {r11, lr}
    sub sp, sp, #16
    add r12, sp, #8
    str r12, [sp]
    bl __divmoddi4
    ldr r2, [sp, #8]
    ldr r3, [sp, #12]
    add sp, sp, #16
    pop {r11, pc}
    .size __aeabi_ldivmod, .-__aeabi_ldivmod

    .align 2
    .global __aeabi_uldivmod
    .type __aeabi_uldivmod, %function
__aeabi_uldivmod:
    push {r11, lr}
    sub sp, sp, #16
    add r12, sp, #8
    str r12, [sp]
    bl __udivmoddi4
    ldr r2, [sp, #8]
    ldr r3, [sp, #12]
    add sp, sp, #16
    pop {r11, pc}
    .size __aeabi_uldivmod, .-__aeabi_uldivmod

// Android 5 Lifevibes sound effects also import 32-bit division helpers.
// Bitwise division avoids a dependency on compiler-rt's private aliases.
// Internal helper: quotient in r0, remainder in r1. r0-r3 and ip are scratch.
    .align 2
    .type elharika_udivmod32, %function
elharika_udivmod32:
    cmp r1, #0
    beq 4f
    mov r2, #0
    mov r3, #0
    mov ip, #32
1:
    movs r0, r0, lsl #1
    adcs r3, r3, r3
    bcs 2f
    cmp r3, r1
    bcc 3f
2:
    sub r3, r3, r1
    add r2, r2, r2
    add r2, r2, #1
    b 5f
3:
    add r2, r2, r2
5:
    subs ip, ip, #1
    bne 1b
    mov r0, r2
    mov r1, r3
    bx lr
4:
    mov r1, r0
    mov r0, #0
    bx lr
    .size elharika_udivmod32, .-elharika_udivmod32

// Signed division follows ARM EABI truncation toward zero.
    .align 2
    .type elharika_idivmod32, %function
elharika_idivmod32:
    push {r4-r6, lr}
    mov r4, r0
    mov r5, r1
    cmp r0, #0
    rsblt r0, r0, #0
    cmp r1, #0
    rsblt r1, r1, #0
    bl elharika_udivmod32
    cmp r4, #0
    rsblt r1, r1, #0
    eor r6, r4, r5
    cmp r6, #0
    rsblt r0, r0, #0
    pop {r4-r6, pc}
    .size elharika_idivmod32, .-elharika_idivmod32

// The divmod calling convention returns quotient in r0 and remainder in r1.
    .align 2
    .global __aeabi_idiv
    .type __aeabi_idiv, %function
__aeabi_idiv:
    b elharika_idivmod32
    .size __aeabi_idiv, .-__aeabi_idiv

    .align 2
    .global __aeabi_uidiv
    .type __aeabi_uidiv, %function
__aeabi_uidiv:
    b elharika_udivmod32
    .size __aeabi_uidiv, .-__aeabi_uidiv

    .align 2
    .global __aeabi_idivmod
    .type __aeabi_idivmod, %function
__aeabi_idivmod:
    b elharika_idivmod32
    .size __aeabi_idivmod, .-__aeabi_idivmod

    .align 2
    .global __aeabi_uidivmod
    .type __aeabi_uidivmod, %function
__aeabi_uidivmod:
    b elharika_udivmod32
    .size __aeabi_uidivmod, .-__aeabi_uidivmod

// Count set bits without depending on another dynamically exported builtin.
    .align 2
    .global __popcountsi2
    .type __popcountsi2, %function
__popcountsi2:
    mov r1, #0
1:
    cmp r0, #0
    beq 2f
    sub r2, r0, #1
    and r0, r0, r2
    add r1, r1, #1
    b 1b
2:
    mov r0, r1
    bx lr
    .size __popcountsi2, .-__popcountsi2
