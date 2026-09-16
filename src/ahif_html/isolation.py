"""Linux deterministic CLI sandbox: seccomp socket/exec denial and rlimits.

This is a worker boundary, not a complete hostile native parser sandbox. Library
calls do not automatically change the embedding process's security policy.
"""
from __future__ import annotations
import ctypes
import errno
import resource
import signal
from .common import Failure

def deterministic_worker(seconds=60,memory_mib=1024):
    resource.setrlimit(resource.RLIMIT_AS,(memory_mib*1024*1024,memory_mib*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(seconds,seconds+1))
    resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024*1024,64*1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    def timeout(*_):raise Failure('worker_wall_limit','resource_limit')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(seconds)
    try:
        lib=ctypes.CDLL('libseccomp.so.2',use_errno=True)
        lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
        lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
        lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
        lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_release.argtypes=[ctypes.c_void_p]
        ctx=lib.seccomp_init(0x7fff0000)
        if not ctx:raise RuntimeError('init')
        denied=[]
        try:
            for name in ('socket','socketpair','connect','bind','listen','accept','accept4','sendto','sendmsg','sendmmsg','recvfrom','recvmsg','recvmmsg','execve','execveat'):
                num=lib.seccomp_syscall_resolve_name(name.encode())
                if num>=0:
                    if lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,num,0)!=0:raise RuntimeError('rule')
                    denied.append(name)
            if lib.seccomp_load(ctx)!=0:raise RuntimeError('load')
        finally:lib.seccomp_release(ctx)
    except (OSError,RuntimeError) as exc:raise Failure('os_isolation_unavailable') from exc
    return {'method':'Linux libseccomp default-allow with network and exec syscall denial','denied_syscalls':denied,'address_space_mib':memory_mib,'cpu_seconds':seconds,'wall_seconds':seconds,'filesystem':'validated explicit paths; no kernel filesystem jail','scope':'deterministic CLI process and inherited descendants'}
