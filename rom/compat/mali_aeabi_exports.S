// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// Export ARM EABI entry points required by the exact SM-P900 Android 5 Mali blob.
// The implementations are provided by the statically linked compiler-rt builtins.
// These wrappers exist so the legacy EABI names are present in the shared
// library dynamic symbol table used by Android's prebuilt ELF checker.

    .syntax unified
    .arm
    .text
    .p2align 2

    .macro ELHARIKA_AEABI_EXPORT name, target
    .global \name
    .type \name, %function
\name:
    b \target
    .size \name, .-\name
    .endm

ELHARIKA_AEABI_EXPORT __aeabi_d2lz,  __fixdfdi
ELHARIKA_AEABI_EXPORT __aeabi_d2ulz, __fixunsdfdi
ELHARIKA_AEABI_EXPORT __aeabi_f2lz,  __fixsfdi
ELHARIKA_AEABI_EXPORT __aeabi_f2ulz, __fixunssfdi
ELHARIKA_AEABI_EXPORT __aeabi_l2d,   __floatdidf
ELHARIKA_AEABI_EXPORT __aeabi_l2f,   __floatdisf
ELHARIKA_AEABI_EXPORT __aeabi_llsr,  __lshrdi3
ELHARIKA_AEABI_EXPORT __aeabi_ul2d,  __floatundidf
ELHARIKA_AEABI_EXPORT __aeabi_ul2f,  __floatundisf
