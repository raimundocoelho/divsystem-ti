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


@register.filter
def has_role(user, min_role: str) -> bool:
    """`{% if user|has_role:'gestor' %}` — true se papel >= min_role."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_global_admin", False):
        return True
    levels = {"operador": 1, "tecnico": 2, "gestor": 3, "admin": 4}
    return levels.get(getattr(user, "role", ""), 0) >= levels.get(min_role, 0)


@register.filter
def humanize_uptime(value) -> str:
    """`{{ uptime_seconds|humanize_uptime }}` → "5d 12h", "9h 23min", "45min"."""
    try:
        s = int(value)
    except (TypeError, ValueError):
        return "—"
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}min"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h {m:02d}min"
    d, h = divmod(h, 24)
    return f"{d}d {h}h"


@register.filter
def used_pct(free, total) -> int:
    """`{{ free|used_pct:total }}` → percentual USADO (0..100)."""
    try:
        f = float(free)
        t = float(total)
        if t <= 0:
            return 0
        return max(0, min(100, round((t - f) / t * 100)))
    except (TypeError, ValueError):
        return 0


@register.filter
def free_pct(free, total) -> int:
    """`{{ free|free_pct:total }}` → percentual LIVRE (0..100)."""
    try:
        f = float(free)
        t = float(total)
        if t <= 0:
            return 0
        return max(0, min(100, round(f / t * 100)))
    except (TypeError, ValueError):
        return 0


@register.filter
def format_mac(value) -> str:
    """`{{ mac|format_mac }}` → "F4:D3:F2:2A:1B:2C" a partir de "F4D3F22A1B2C"."""
    if not value:
        return "—"
    s = str(value).replace(":", "").replace("-", "").upper()
    if len(s) == 12:
        return ":".join(s[i:i+2] for i in range(0, 12, 2))
    return value


@register.filter
def get_item(d, key):
    """`{{ mydict|get_item:somekey }}` — lookup em dict pra usar em template."""
    if d is None:
        return None
    try:
        return d.get(key)
    except AttributeError:
        return None
