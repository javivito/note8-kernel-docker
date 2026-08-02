#!/usr/bin/env python3
"""
Fix Samsung kernel bug: ipc/namespace.c
create_ipc_ns() llama mq_init_ns(ns) antes de inicializar ns->user_ns -> NULL pointer crash
Fix: mover ns->user_ns = get_user_ns(user_ns) ANTES de mq_init_ns(ns)
"""
import sys

with open('ipc/namespace.c', 'r') as f:
    src = f.read()

OLD = (
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

NEW = (
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

if OLD not in src:
    print("ERROR: patron no encontrado en ipc/namespace.c", file=sys.stderr)
    print("Contexto actual:", file=sys.stderr)
    idx = src.find('atomic_set(&ns->count')
    print(src[idx:idx+400], file=sys.stderr)
    sys.exit(1)

src = src.replace(OLD, NEW, 1)

with open('ipc/namespace.c', 'w') as f:
    f.write(src)

print("Patch aplicado OK")
print("Resultado:")
idx = src.find('atomic_set(&ns->count')
print(src[idx:idx+350])
