"""Armazena o tenant ativo na thread atual.

A escolha por thread-local — em vez de passar `tenant` por argumento — replica o
comportamento do `TenantScope` global do Laravel: qualquer queryset filtra
automaticamente pelo tenant resolvido no início do request.
"""
from contextlib import contextmanager
from threading import local

_state = local()


def set_current_tenant(tenant):
    _state.tenant = tenant


def get_current_tenant():
    return getattr(_state, "tenant", None)


def clear_current_tenant():
    if hasattr(_state, "tenant"):
        del _state.tenant


@contextmanager
def use_tenant(tenant):
    previous = get_current_tenant()
    set_current_tenant(tenant)
    try:
        yield tenant
    finally:
        if previous is None:
            clear_current_tenant()
        else:
            set_current_tenant(previous)
