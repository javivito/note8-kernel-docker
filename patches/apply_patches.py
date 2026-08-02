#!/usr/bin/env python3
"""
Patches para Samsung kernel 4.4 (android_kernel_samsung_universal8895 lineage-19.1):

Patch 1: ipc/namespace.c
  Bug: create_ipc_ns() llama mq_init_ns(ns) antes de inicializar ns->user_ns -> NULL pointer crash
  Fix: mover ns->user_ns = get_user_ns(user_ns) ANTES de mq_init_ns(ns)
  Efecto: docker run --net=host deja de causar kernel panic

Patch 2: kernel/bpf/syscall.c
  Bug: BPF_PROG_QUERY (cmd=12) no implementado -> Samsung LSM lo rechaza con EINVAL
       antes de llegar al switch, por lo que un case 12: en el switch no basta.
  Fix: early return ENOENT al inicio de SYSCALL_DEFINE3(bpf,...), antes de security_bpf()
  Efecto: runc 1.4.0 interpreta ENOENT como "sin programas adjuntos" y continua
"""
import sys
import os

# ============================================================
# Patch 1: ipc/namespace.c - fix mq_init_ns NULL pointer
# ============================================================

print("=== Patch 1: ipc/namespace.c ===")

with open('ipc/namespace.c', 'r') as f:
    src = f.read()

OLD1 = (
    '\tatomic_set(&ns->count, 1);\n'
    '\terr = mq_init_ns(ns);\n'
    '\tif (err) {\n'
    '\t\tns_free_inum(&ns->ns);\n'
    '\t\tkfree(ns);\n'
    '\t\treturn ERR_PTR(err);\n'
    '\t}\n'
    '\tatomic_inc(&nr_ipc_ns);\n'
    '\n'
    '\tsem_init_ns(ns);\n'
    '\tmsg_init_ns(ns);\n'
    '\tshm_init_ns(ns);\n'
    '\n'
    '\tns->user_ns = get_user_ns(user_ns);\n'
)

NEW1 = (
    '\tatomic_set(&ns->count, 1);\n'
    '\tns->user_ns = get_user_ns(user_ns);\n'
    '\terr = mq_init_ns(ns);\n'
    '\tif (err) {\n'
    '\t\tput_user_ns(ns->user_ns);\n'
    '\t\tns_free_inum(&ns->ns);\n'
    '\t\tkfree(ns);\n'
    '\t\treturn ERR_PTR(err);\n'
    '\t}\n'
    '\tatomic_inc(&nr_ipc_ns);\n'
    '\n'
    '\tsem_init_ns(ns);\n'
    '\tmsg_init_ns(ns);\n'
    '\tshm_init_ns(ns);\n'
)

if OLD1 not in src:
    print("ERROR: patron no encontrado en ipc/namespace.c", file=sys.stderr)
    idx = src.find('atomic_set(&ns->count')
    print(src[idx:idx+400], file=sys.stderr)
    sys.exit(1)

src = src.replace(OLD1, NEW1, 1)

with open('ipc/namespace.c', 'w') as f:
    f.write(src)

print("Patch 1 OK: mq_init_ns crash fix aplicado")
idx = src.find('atomic_set(&ns->count')
print(src[idx:idx+300])

# ============================================================
# Patch 2: kernel/bpf/syscall.c - BPF_PROG_QUERY early stub
# ============================================================

print("\n=== Patch 2: kernel/bpf/syscall.c ===")

bpf_path = 'kernel/bpf/syscall.c'
if not os.path.exists(bpf_path):
    print(f"ERROR: {bpf_path} no encontrado", file=sys.stderr)
    sys.exit(1)

with open(bpf_path, 'r') as f:
    bsrc = f.read()

# Check if already patched
STUB_MARKER = '/* BPF_PROG_QUERY early stub'
if STUB_MARKER in bsrc:
    print("BPF_PROG_QUERY stub ya presente, omitiendo patch 2")
else:
    # Strategy: add EARLY return at the start of SYSCALL_DEFINE3(bpf,...),
    # BEFORE security_bpf() and BEFORE any size validation.
    # This bypasses Samsung's LSM which rejects unknown cmds with EINVAL.
    # cmd=12 = BPF_PROG_QUERY. ENOENT = runc treats as "no programs attached".

    DEFINE_PAT = 'SYSCALL_DEFINE3(bpf, int, cmd, union bpf_attr __user *, uattr, unsigned int, size)\n{'

    if DEFINE_PAT not in bsrc:
        print("ERROR: no se encontro SYSCALL_DEFINE3(bpf,...)", file=sys.stderr)
        idx = bsrc.find('SYSCALL_DEFINE3(bpf')
        print(f"Contexto encontrado: {bsrc[idx:idx+200]!r}", file=sys.stderr)
        sys.exit(1)

    EARLY_STUB = (
        'SYSCALL_DEFINE3(bpf, int, cmd, union bpf_attr __user *, uattr, unsigned int, size)\n'
        '{\n'
        '\t/* BPF_PROG_QUERY early stub: cmd=12 rejected by Samsung LSM before switch.\n'
        '\t * Return ENOENT so runc 1.4.0 treats as "no programs attached". */\n'
        '\tif (cmd == 12)\n'
        '\t\treturn -ENOENT;\n'
    )

    bsrc = bsrc.replace(DEFINE_PAT, EARLY_STUB, 1)

    with open(bpf_path, 'w') as f:
        f.write(bsrc)

    idx = bsrc.find(STUB_MARKER)
    print(f"Patch 2 OK: early stub en posicion {idx}")
    print(bsrc[max(0,idx-20):idx+300])

print("\nTodos los patches aplicados OK")
