"""Autenticação Bearer para o agente — equivalente ao Sanctum do Laravel.

O agente envia `Authorization: Bearer <token>` e o middleware do tenant é ignorado
(o agente nunca é um `User`), mas escrevemos `request.agent_token` e
`request.tenant` para reaproveitar contexto.
"""
from rest_framework import authentication, exceptions

from apps.core.threadlocal import set_current_tenant

from .models import AgentToken


class AgentTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
        if len(auth) != 2:
            raise exceptions.AuthenticationFailed("Header Authorization malformado.")
        try:
            token_value = auth[1].decode()
        except UnicodeError:
            raise exceptions.AuthenticationFailed("Token inválido.")

        try:
            agent = AgentToken.all_tenants.select_related("tenant").get(token=token_value, active=True)
        except AgentToken.DoesNotExist:
            raise exceptions.AuthenticationFailed("Token inválido ou inativo.")

        request.agent_token = agent
        request.tenant = agent.tenant
        set_current_tenant(agent.tenant)
        return (AgentUser(agent), agent)

    def authenticate_header(self, request):
        return self.keyword


class AgentUser:
    """Stub que satisfaz `request.user.is_authenticated` para DRF.

    Não é um `User` real — o agente é um *cliente máquina*, não um humano.
    """

    is_authenticated = True
    is_anonymous = False
    is_active = True
    is_staff = False
    is_superuser = False

    def __init__(self, agent: AgentToken):
        self.agent = agent
        self.id = f"agent:{agent.pk}"
        self.pk = self.id

    def __str__(self) -> str:
        return f"agent:{self.agent.name}"

    def get_username(self) -> str:
        return f"agent:{self.agent.pk}"

    @property
    def tenant(self):
        return self.agent.tenant

    @property
    def tenant_id(self):
        return self.agent.tenant_id
