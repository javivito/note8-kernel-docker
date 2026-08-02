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

# Check if BPF_PROG_QUERY already handled (by name or numeric stub)
if 'BPF_PROG_QUERY' in bsrc or 'case 12: /* BPF_PROG_QUERY' in bsrc:
    print("BPF_PROG_QUERY ya presente en syscall.c, omitiendo patch 2")
else:
    # Find the default: return -EINVAL; in the bpf() syscall
    # We need to insert BPF_PROG_QUERY case before the default
    # Look for the pattern of BPF_PROG_DETACH or BPF_PROG_ATTACH case then default

    # Pattern: after BPF_PROG_DETACH case, before "default:"
    # In Samsung 4.4 with CGROUP_BPF, the switch has ATTACH and DETACH but not QUERY

    # The actual Samsung 4.4 kernel structure has:
    #   #ifdef CONFIG_CGROUP_BPF
    #   case BPF_PROG_ATTACH: ... break;
    #   case BPF_PROG_DETACH: ... break;
    #   #endif
    #   default: err = -EINVAL; break;
    # We insert BPF_PROG_QUERY inside the #ifdef block after DETACH

    CANDIDATES = [
        # Main pattern: inside #ifdef CGROUP_BPF, after DETACH, before #endif
        # BPF_PROG_QUERY not defined in Samsung 4.4 headers, use numeric value 12
        (
            '\tcase BPF_PROG_DETACH:\n\t\terr = bpf_prog_detach(&attr);\n\t\tbreak;\n#endif\n',
            '\tcase BPF_PROG_DETACH:\n\t\terr = bpf_prog_detach(&attr);\n\t\tbreak;\n'
            '\tcase 12: /* BPF_PROG_QUERY - stub: no programs attached - runc 1.4.0 compat */\n\t\terr = -ENOENT;\n\t\tbreak;\n'
            '#endif\n'
        ),
        # Variant with extra newline before #endif
        (
            '\tcase BPF_PROG_DETACH:\n\t\terr = bpf_prog_detach(&attr);\n\t\tbreak;\n\n#endif\n',
            '\tcase BPF_PROG_DETACH:\n\t\terr = bpf_prog_detach(&attr);\n\t\tbreak;\n'
            '\tcase 12: /* BPF_PROG_QUERY - stub: no programs attached - runc 1.4.0 compat */\n\t\terr = -ENOENT;\n\t\tbreak;\n'
            '\n#endif\n'
        ),
        # Fallback: before default case
        (
            '\tdefault:\n\t\terr = -EINVAL;\n\t\tbreak;\n\t}\n\n\treturn err;\n}',
            '\tcase 12: /* BPF_PROG_QUERY - stub: no programs attached - runc 1.4.0 compat */\n\t\terr = -ENOENT;\n\t\tbreak;\n'
            '\tdefault:\n\t\terr = -EINVAL;\n\t\tbreak;\n\t}\n\n\treturn err;\n}'
        ),
    ]

    patched = False
    for OLD2, NEW2 in CANDIDATES:
        if OLD2 in bsrc:
            bsrc = bsrc.replace(OLD2, NEW2, 1)
            patched = True
            print(f"Patch 2 OK: BPF_PROG_QUERY stub añadido")
            break

    if not patched:
        print("WARNING: patron BPF switch no encontrado, buscando alternativa...", file=sys.stderr)
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
    idx = bsrc.find('case 12: /* BPF_PROG_QUERY')
    print(f"Verificacion: case 12 BPF_PROG_QUERY en posicion {idx}")
    print(bsrc[max(0,idx-100):idx+200])

print("\nTodos los patches aplicados OK")
