// SPDX-License-Identifier: 0BSD
// Freestanding Linux helper: copy ONLY the known system_file SELinux xattr.
// No libselinux dependency, policy changes, permissive switch, or setuid bit.
typedef unsigned long word;
#ifdef LABEL_COPY_TEST
static const char attribute[] = "user.elharika-label-test";
#else
static const char attribute[] = "security.selinux";
#endif
static const char expected[] = "u:object_r:system_file:s0";

#if defined(__arm__)
#define NR_WRITE 4
#define NR_GETXATTR 229
#define NR_SETXATTR 226
static long sys5(long n, word a, word b, word c, word d, word e) {
    register long r0 __asm__("r0") = (long)a;
    register word r1 __asm__("r1") = b, r2 __asm__("r2") = c;
    register word r3 __asm__("r3") = d, r4 __asm__("r4") = e;
    register long r7 __asm__("r7") = n;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r4), "r"(r7) : "memory", "cc");
    return r0;
}
__asm__(".global _start\n.type _start,%function\n_start:\nmov r0,sp\nbl label_main\nmov r7,#1\nsvc 0\n");
#elif defined(__x86_64__) && defined(LABEL_COPY_TEST)
#define NR_WRITE 1
#define NR_GETXATTR 191
#define NR_SETXATTR 188
static long sys5(long n, word a, word b, word c, word d, word e) {
    register word r10 __asm__("r10") = d, r8 __asm__("r8") = e;
    __asm__ volatile("syscall" : "+a"(n) : "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8) : "rcx", "r11", "memory", "cc");
    return n;
}
__asm__(".global _start\n.type _start,@function\n_start:\nmov %rsp,%rdi\nand $-16,%rsp\ncall label_main\nmov %rax,%rdi\nmov $60,%rax\nsyscall\n");
#else
#error Production helper must be ARM32; x86_64 is only for host tests.
#endif

static void print(const char *s) {
    word n = 0;
    while (s[n]) ++n;
    (void)sys5(NR_WRITE, 2, (word)s, n, 0, 0);
}
static int error(const char *stage, long status) {
    char digits[24]; word n = 0; word number = status < 0 ? (word)(-status) : (word)status;
    static const word powers[] = {1000000000,100000000,10000000,1000000,100000,10000,1000,100,10,1};
    print("label-copy: "); print(stage); print("; errno/status=");
    // No division: ARMv7 soft division would introduce a libgcc dependency.
    for (word i = 0; i < sizeof(powers)/sizeof(powers[0]); ++i) {
        unsigned int digit = 0;
        while (number >= powers[i]) { number -= powers[i]; ++digit; }
        if (digit || n || powers[i] == 1) digits[n++] = (char)('0' + digit);
    }
    (void)sys5(NR_WRITE, 2, (word)digits, n, 0, 0);
    print("\n"); return 1;
}
static int matches(const char *bytes, long size) {
    if (size != (long)sizeof(expected)) return 0;
    for (word i = 0; i < sizeof(expected); ++i)
        if (bytes[i] != expected[i]) return 0;
    return 1;
}
int label_main(word *stack) {
    if (stack[0] != 3) { print("usage: label-copy REFERENCE TARGET\n"); return 2; }
    const char *reference = (const char *)stack[2], *target = (const char *)stack[3];
    char buffer[128];
    long n = sys5(NR_GETXATTR, (word)reference, (word)attribute, (word)buffer, sizeof(buffer), 0);
    if (n < 0) return error("getxattr(reference)", n);
    if (!matches(buffer, n)) { print("label-copy: reference is not the expected system_file label\n"); return 1; }
    n = sys5(NR_SETXATTR, (word)target, (word)attribute, (word)buffer, (word)n, 0);
    if (n < 0) return error("setxattr(target)", n);
    n = sys5(NR_GETXATTR, (word)target, (word)attribute, (word)buffer, sizeof(buffer), 0);
    if (n < 0) return error("getxattr(target)", n);
    if (!matches(buffer, n)) { print("label-copy: target label verification failed\n"); return 1; }
    print("label-copy: system_file label copied and verified\n");
    return 0;
}
