#!/usr/bin/env python3
"""
Patches para Samsung kernel 4.4 (android_kernel_samsung_universal8895 lineage-19.1):

Patch 1: ipc/namespace.c
  Bug: create_ipc_ns() llama mq_init_ns(ns) antes de inicializar ns->user_ns -> NULL pointer crash
  Fix: mover ns->user_ns = get_user_ns(user_ns) ANTES de mq_init_ns(ns)
  Efecto: docker run --net=host deja de causar kernel panic

Patch 2: kernel/bpf/syscall.c
  Problema: Samsung LSM bloquea con EINVAL TODOS los comandos BPF antes del switch:
    - cmd=12 (BPF_PROG_QUERY): runc lo llama para ver programas adjuntos
    - cmd=5  (BPF_PROG_LOAD): runc carga el filtro BPF de dispositivos (prog_type=15)
    - cmd=8  (BPF_PROG_ATTACH): runc adjunta el filtro al cgroup
    - cmd=9  (BPF_PROG_DETACH): runc desadjunta al parar el contenedor
  Fix: stubs antes de security_bpf() para cada comando:
    - cmd=12 -> ENOENT ("sin programas") para que runc intente cargar uno nuevo
    - cmd=5 con prog_type=15 (BPF_PROG_TYPE_CGROUP_DEVICE) -> fd anonimo (stub)
    - cmd=8/9 con attach_type=7 (BPF_CGROUP_DEVICE) -> 0 (exito)
  Efecto: docker run funciona (sin filtrado real de dispositivos, todos permitidos)
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
# Patch 2: kernel/bpf/syscall.c - BPF cgroup device stubs
# ============================================================

print("\n=== Patch 2: kernel/bpf/syscall.c ===")

bpf_path = 'kernel/bpf/syscall.c'
if not os.path.exists(bpf_path):
    print(f"ERROR: {bpf_path} no encontrado", file=sys.stderr)
    sys.exit(1)

with open(bpf_path, 'r') as f:
    bsrc = f.read()

# Check if already patched
STUB_MARKER = '/* BPF cgroup device stubs'
if STUB_MARKER in bsrc:
    print("BPF cgroup device stubs ya presentes, omitiendo patch 2")
else:
    # Match SYSCALL_DEFINE3(bpf,...) and prepend static fops + stubs
    DEFINE_PAT = 'SYSCALL_DEFINE3(bpf, int, cmd, union bpf_attr __user *, uattr, unsigned int, size)\n{'

    if DEFINE_PAT not in bsrc:
        print("ERROR: no se encontro SYSCALL_DEFINE3(bpf,...)", file=sys.stderr)
        idx = bsrc.find('SYSCALL_DEFINE3(bpf')
        print(f"Contexto encontrado: {bsrc[idx:idx+200]!r}", file=sys.stderr)
        sys.exit(1)

    # The replacement prepends:
    # 1. Static file_operations for the stub BPF prog fd
    # 2. Early-return stubs inside SYSCALL_DEFINE3 before security_bpf()
    #
    # Layout of bpf_attr for the relevant commands:
    #   BPF_PROG_LOAD  (cmd=5): offset 0 = prog_type (u32)
    #   BPF_PROG_ATTACH (cmd=8): offset 0=target_fd, 4=prog_fd, 8=attach_type (u32)
    #   BPF_PROG_DETACH (cmd=9): same layout as ATTACH
    #   BPF_PROG_QUERY (cmd=12): offset 0=target_fd, 4=attach_type (u32)
    #
    # BPF_PROG_TYPE_CGROUP_DEVICE = 15
    # BPF_CGROUP_DEVICE           = 7

    EARLY_STUB = (
        '/* BPF cgroup device stubs: Samsung LSM blocks all BPF calls before the switch.\n'
        ' * These stubs bypass the LSM for cgroup device operations so runc 1.4.0 can\n'
        ' * start containers. Device filtering is not enforced (all devices allowed). */\n'
        'static int bpf_stub_prog_release(struct inode *inode, struct file *filp)\n'
        '{\n'
        '\treturn 0;\n'
        '}\n'
        '\n'
        'static const struct file_operations bpf_stub_prog_fops = {\n'
        '\t.release = bpf_stub_prog_release,\n'
        '};\n'
        '\n'
        'SYSCALL_DEFINE3(bpf, int, cmd, union bpf_attr __user *, uattr, unsigned int, size)\n'
        '{\n'
        '\t__u32 __bpf_u32;\n'
        '\n'
        '\t/* cmd=12 BPF_PROG_QUERY: ENOENT = no programs attached.\n'
        '\t * Samsung LSM returns EINVAL for this cmd; we return ENOENT so\n'
        '\t * runc treats the cgroup as having no existing device filter. */\n'
        '\tif (cmd == 12)\n'
        '\t\treturn -ENOENT;\n'
        '\n'
        '\t/* cmd=5 BPF_PROG_LOAD for prog_type=15 (BPF_PROG_TYPE_CGROUP_DEVICE):\n'
        '\t * Samsung LSM blocks prog loading. Return an anonymous fd so runc\n'
        '\t * has a handle to pass to BPF_PROG_ATTACH below. */\n'
        '\tif (cmd == 5 && size >= sizeof(__u32)) {\n'
        '\t\tif (!get_user(__bpf_u32, (__u32 __user *)uattr) &&\n'
        '\t\t    __bpf_u32 == 15)\n'
        '\t\t\treturn anon_inode_getfd("[bpf]", &bpf_stub_prog_fops,\n'
        '\t\t\t\t\t       NULL, O_RDWR | O_CLOEXEC);\n'
        '\t}\n'
        '\n'
        '\t/* cmd=8 BPF_PROG_ATTACH, cmd=9 BPF_PROG_DETACH for\n'
        '\t * attach_type=7 (BPF_CGROUP_DEVICE): stub success. */\n'
        '\tif ((cmd == 8 || cmd == 9) && size >= 12) {\n'
        '\t\tif (!get_user(__bpf_u32,\n'
        '\t\t\t      (__u32 __user *)((char __user *)uattr + 8)) &&\n'
        '\t\t    __bpf_u32 == 7)\n'
        '\t\t\treturn 0;\n'
        '\t}\n'
        '\n'
    )

    bsrc = bsrc.replace(DEFINE_PAT, EARLY_STUB, 1)

    with open(bpf_path, 'w') as f:
        f.write(bsrc)

    idx = bsrc.find(STUB_MARKER)
    print(f"Patch 2 OK: BPF cgroup device stubs en posicion {idx}")
    print(bsrc[max(0,idx-5):idx+800])

print("\nTodos los patches aplicados OK")
