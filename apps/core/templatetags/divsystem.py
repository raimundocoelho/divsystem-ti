"""Template tags compartilhadas — disponíveis como builtins em todos os templates."""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def icon(name, size: str = "1.25em", extra_class: str = ""):
    """Renderiza um ícone Iconify.

    Uso: {% icon "lucide:gauge" "1.5em" "text-blue-500" %}
    Iconify entrega via web component (`<iconify-icon>`) — basta o JS estar carregado.
    """
    classes = f"iconify-inline {extra_class}".strip()
    return format_html(
        '<iconify-icon icon="{}" width="{}" height="{}" class="{}" aria-hidden="true"></iconify-icon>',
        name,
        size,
        size,
        classes,
    )


@register.filter
def role_badge(user):
    if not user or not user.is_authenticated:
        return mark_safe("")
    role = getattr(user, "role", None)
    if not role:
        return mark_safe("")
    color_map = {
        "admin": "bg-red-100 text-red-700 ring-red-600/20",
        "gestor": "bg-blue-100 text-blue-700 ring-blue-600/20",
        "tecnico": "bg-amber-100 text-amber-700 ring-amber-600/20",
        "operador": "bg-zinc-100 text-zinc-700 ring-zinc-600/20",
    }
    label_map = {
        "admin": "Administrador",
        "gestor": "Gestor",
        "tecnico": "Técnico",
        "operador": "Operador",
    }
    classes = color_map.get(role, "bg-zinc-100 text-zinc-700")
    label = label_map.get(role, role)
    return format_html(
        '<span class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset {}">{}</span>',
        classes,
        label,
    )


@register.filter
def initials(user):
    if not user:
        return ""
    name = getattr(user, "name", "") or getattr(user, "get_full_name", lambda: "")() or user.email
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return user.email[:2].upper() if getattr(user, "email", "") else "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.simple_tag(takes_context=True)
def active_url(context, *url_patterns):
    """Retorna 'is-active' se o request.path bate com algum dos patterns."""
    path = context["request"].path
    for pattern in url_patterns:
        if pattern == "/" and path == "/":
            return "is-active"
        if pattern != "/" and path.startswith(pattern):
            return "is-active"
    return ""
