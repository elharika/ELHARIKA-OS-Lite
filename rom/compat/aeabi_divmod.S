// Adapted from LLVM compiler-rt release_32 lib/arm/aeabi_{l,ul}divmod.S.
// The original sources are dual licensed under MIT and University of Illinois
// Open Source licenses; see LICENSE.TXT in this directory.
// ARM EABI returns quotient in r0:r1 and remainder in r2:r3.

    .syntax unified
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
