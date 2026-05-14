import uuid
from pathlib import PurePosixPath

from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView, View

from apps.agentes.models import AgentToken, RemoteCommand
from apps.core.permissions import UserRole
from apps.core.storages import CloudflareR2Storage
from apps.core.views_mixins import RoleRequiredMixin
from apps.organizacoes.models import Secretaria, Setor

from .forms import SettingForm
from .models import Setting, Wallpaper


# ───────────────────────── Home (cards) ─────────────────────────

class ConfiguracoesHomeView(RoleRequiredMixin, TemplateView):
    required_role = UserRole.ADMIN
    template_name = "configuracoes/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["wallpapers"] = Wallpaper.objects.select_related("secretaria", "setor", "uploaded_by").order_by("-created_at")[:5]
        ctx["secretarias_list"] = Secretaria.objects.filter(ativo=True).order_by("nome")
        # Lista plana de setores pro select encadeado (Alpine filtra client-side).
        ctx["setores_all"] = list(
            Setor.objects.filter(ativo=True).values("id", "nome", "secretaria_id").order_by("nome")
        )
        return ctx


# ───────────────────────── Wallpaper ─────────────────────────

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


class WallpaperUploadView(RoleRequiredMixin, View):
    """POST: recebe upload + escopo, joga no R2, dispara RemoteCommands."""

    required_role = UserRole.ADMIN

    def post(self, request):
        upload = request.FILES.get("image")
        if not upload:
            messages.error(request, "Selecione uma imagem.")
            return redirect("configuracoes:list")

        ext = PurePosixPath(upload.name).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXT:
            messages.error(request, f"Extensao nao suportada: {ext}. Use JPG, PNG ou WEBP.")
            return redirect("configuracoes:list")
        if upload.size > MAX_IMAGE_BYTES:
            messages.error(request, f"Arquivo grande demais ({upload.size // 1024} KB). Maximo 5 MB.")
            return redirect("configuracoes:list")

        sec_id = (request.POST.get("secretaria_id") or "").strip() or None
        set_id = (request.POST.get("setor_id") or "").strip() or None

        # Validacao basica de escopo.
        if sec_id and not Secretaria.objects.filter(pk=sec_id, ativo=True).exists():
            messages.error(request, "Secretaria invalida.")
            return redirect("configuracoes:list")
        if set_id:
            qs = Setor.objects.filter(pk=set_id, ativo=True)
            if sec_id:
                qs = qs.filter(secretaria_id=sec_id)
            if not qs.exists():
                messages.error(request, "Setor invalido pra essa secretaria.")
                return redirect("configuracoes:list")

        # Upload R2 — key versionada por uuid pra cache-busting nos agentes.
        storage = CloudflareR2Storage(location="wallpapers")
        key_name = f"{uuid.uuid4().hex}{ext}"
        upload.seek(0)
        saved_name = storage.save(key_name, upload)
        public_url = storage.url(saved_name)

        wp = Wallpaper.objects.create(
            secretaria_id=sec_id,
            setor_id=set_id,
            image_url=public_url,
            image_key=storage._key(saved_name),
            original_filename=upload.name[:255],
            file_size=upload.size,
            uploaded_by=request.user,
        )

        # Enfileira RemoteCommand pra agentes do escopo.
        count = self._dispatch(wp)
        wp.applied_at = timezone.now()
        wp.applied_count = count
        wp.save(update_fields=["applied_at", "applied_count"])

        messages.success(
            request, f"Papel de parede enviado pra {count} agente(s) ({wp.scope_label})."
        )
        return redirect("configuracoes:list")

    @staticmethod
    def _dispatch(wp: Wallpaper) -> int:
        """Cria 1 RemoteCommand `set_wallpaper` por agente ativo no escopo."""
        qs = AgentToken.objects.filter(active=True)
        if wp.secretaria_id:
            qs = qs.filter(secretaria_id=wp.secretaria_id)
        if wp.setor_id:
            qs = qs.filter(setor_id=wp.setor_id)

        payload = {"image_url": wp.image_url}
        cmds = [
            RemoteCommand(
                tenant_id=agent.tenant_id,
                agent_token=agent,
                command="set_wallpaper",
                payload=payload,
                status=RemoteCommand.Status.PENDING,
                created_by=wp.uploaded_by,
            )
            for agent in qs
        ]
        if cmds:
            RemoteCommand.objects.bulk_create(cmds)
        return len(cmds)


class WallpaperReapplyView(RoleRequiredMixin, View):
    """POST: re-enfileira o `set_wallpaper` de um wallpaper ja existente."""

    required_role = UserRole.ADMIN

    def post(self, request, pk):
        wp = get_object_or_404(Wallpaper, pk=pk)
        count = WallpaperUploadView._dispatch(wp)
        wp.applied_at = timezone.now()
        wp.applied_count = count
        wp.save(update_fields=["applied_at", "applied_count"])
        messages.success(request, f"Re-enviado pra {count} agente(s).")
        return redirect("configuracoes:list")


# ───────────────────────── Setting CRUD (mantido) ─────────────────────────

class SettingListView(RoleRequiredMixin, ListView):
    required_role = UserRole.ADMIN
    template_name = "configuracoes/setting_list.html"
    context_object_name = "settings"
    paginate_by = 50

    def get_queryset(self):
        return Setting.objects.order_by("key")


class SettingCreateView(RoleRequiredMixin, CreateView):
    required_role = UserRole.ADMIN
    model = Setting
    form_class = SettingForm
    template_name = "configuracoes/setting_form.html"
    success_url = reverse_lazy("configuracoes:setting_list")

    def form_valid(self, form):
        messages.success(self.request, f"Configuracao '{form.instance.key}' criada.")
        return super().form_valid(form)


class SettingUpdateView(RoleRequiredMixin, UpdateView):
    required_role = UserRole.ADMIN
    model = Setting
    form_class = SettingForm
    template_name = "configuracoes/setting_form.html"
    success_url = reverse_lazy("configuracoes:setting_list")

    def form_valid(self, form):
        messages.success(self.request, f"Configuracao '{form.instance.key}' atualizada.")
        return super().form_valid(form)


class SettingDeleteView(RoleRequiredMixin, DeleteView):
    required_role = UserRole.ADMIN
    model = Setting
    template_name = "configuracoes/setting_confirm_delete.html"
    success_url = reverse_lazy("configuracoes:setting_list")
