#!/usr/bin/env python3
"""
Patches para Samsung kernel 4.4 (android_kernel_samsung_universal8895 lineage-19.1):

Patch 1: ipc/namespace.c
  Bug: create_ipc_ns() llama mq_init_ns(ns) antes de inicializar ns->user_ns -> NULL pointer crash
  Fix: mover ns->user_ns = get_user_ns(user_ns) ANTES de mq_init_ns(ns)
  Efecto: docker run --net=host deja de causar kernel panic

Patch 2: kernel/bpf/syscall.c
  Bug: BPF_PROG_QUERY (cmd 12) no implementado en Samsung 4.4 -> devuelve EINVAL
  Fix: añadir stub que devuelve ENOENT (sin programas adjuntos)
  Efecto: runc 1.4.0 puede usar BPF cgroup device management en cgroup v2
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
# Patch 2: kernel/bpf/syscall.c - add BPF_PROG_QUERY stub
# ============================================================

print("\n=== Patch 2: kernel/bpf/syscall.c ===")

bpf_path = 'kernel/bpf/syscall.c'
if not os.path.exists(bpf_path):
    print(f"ERROR: {bpf_path} no encontrado", file=sys.stderr)
    sys.exit(1)

with open(bpf_path, 'r') as f:
    bsrc = f.read()

# Check if BPF_PROG_QUERY already handled
if 'BPF_PROG_QUERY' in bsrc:
    print("BPF_PROG_QUERY ya presente en syscall.c, omitiendo patch 2")
else:
    # Find the default: return -EINVAL; in the bpf() syscall
    # We need to insert BPF_PROG_QUERY case before the default
    # Look for the pattern of BPF_PROG_DETACH or BPF_PROG_ATTACH case then default

    # Pattern: after BPF_PROG_DETACH case, before "default:"
    # In Samsung 4.4 with CGROUP_BPF, the switch has ATTACH and DETACH but not QUERY

    CANDIDATES = [
        # Try after BPF_PROG_DETACH
        '\tcase BPF_PROG_DETACH:\n\t\terr = bpf_prog_detach(attr);\n\t\tbreak;\n\tdefault:\n\t\treturn -EINVAL;\n',
        '\tcase BPF_PROG_DETACH:\n\t\terr = bpf_prog_detach(attr);\n\t\tbreak;\n\n\tdefault:\n\t\treturn -EINVAL;\n',
        # Try after BPF_PROG_ATTACH (if DETACH not present)
        '\tcase BPF_PROG_ATTACH:\n\t\terr = bpf_prog_attach(attr);\n\t\tbreak;\n\tdefault:\n\t\treturn -EINVAL;\n',
        '\tcase BPF_PROG_ATTACH:\n\t\terr = bpf_prog_attach(attr);\n\t\tbreak;\n\n\tdefault:\n\t\treturn -EINVAL;\n',
    ]

    # The stub to insert: BPF_PROG_QUERY returns -ENOENT (no programs attached)
    # runc 1.4.0 treats ENOENT as "no existing programs, proceed to attach"
    QUERY_STUB = '\tcase BPF_PROG_QUERY:\n\t\t/* stub: report no programs attached (BPF_PROG_QUERY added for runc compat) */\n\t\treturn -ENOENT;\n'

    patched = False
    for OLD2 in CANDIDATES:
        if OLD2 in bsrc:
            NEW2 = OLD2.replace('\tdefault:\n\t\treturn -EINVAL;\n',
                                QUERY_STUB + '\tdefault:\n\t\treturn -EINVAL;\n')
            bsrc = bsrc.replace(OLD2, NEW2, 1)
            patched = True
            print(f"Patch 2 OK: BPF_PROG_QUERY stub añadido (patron: {OLD2[:60]!r}...)")
            break

    if not patched:
        # Show what we found to help debug
        print("WARNING: patron BPF switch default no encontrado, buscando alternativa...", file=sys.stderr)
        # Show context around 'default:' inside the bpf syscall
        idx = bsrc.find('SYSCALL_DEFINE3(bpf,')
        if idx >= 0:
            end_idx = bsrc.find('\nSYSCALL_', idx + 1)
            syscall_body = bsrc[idx:end_idx if end_idx > 0 else idx + 3000]
            print("Cuerpo del syscall bpf():", file=sys.stderr)
            print(syscall_body[:2000], file=sys.stderr)
        sys.exit(1)

    with open(bpf_path, 'w') as f:
        f.write(bsrc)

    # Verify
    idx = bsrc.find('BPF_PROG_QUERY')
    print(f"Verificacion: BPF_PROG_QUERY en posicion {idx}")
    print(bsrc[max(0,idx-100):idx+200])

print("\nTodos los patches aplicados OK")
