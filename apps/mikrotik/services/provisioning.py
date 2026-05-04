"""Gerador do script de bootstrap para RouterOS (.rsc).

Esse script deve ser colado UMA vez no Terminal do Winbox/WebFig do equipamento
(ou enviado via `import` após upload de arquivo). Ele:

1. Define identidade e senha de admin.
2. Cria a interface WireGuard cliente que disca para o hub.
3. Adiciona o peer servidor.
4. Cria endereço IP na interface WG.
5. Cria usuário dedicado para a API REST com grupo restrito.
6. Configura o firewall: SSH/Winbox/API/REST só pela interface WG.
7. Habilita www-ssl (REST API HTTPS) e gera certificado se necessário.

Pré-requisito: o operador acessou o equipamento em 192.168.88.1 com user/senha
informados no painel ANTES de aplicar o script. O script muda a senha do admin
para a definida no painel.
"""
from __future__ import annotations

from textwrap import dedent

from apps.mikrotik.models import Equipamento


def gerar_script_bootstrap(
    equipamento: Equipamento,
    *,
    server_pubkey: str,
    server_endpoint_host: str,
    server_endpoint_port: int,
    nova_senha_admin: str,
) -> str:
    """Retorna o conteúdo do .rsc para o equipamento."""
    if not equipamento.wg_privkey_device or not equipamento.wg_ip:
        raise ValueError("Equipamento ainda não foi provisionado (faltam chaves WG/IP).")

    identity = f"divsystem-{equipamento.slug or equipamento.pk}"

    script = f"""# === DIVSYSTEM-TI :: bootstrap Mikrotik ===
# Equipamento: {equipamento.nome}  (id={equipamento.pk}, tenant={equipamento.tenant_id})
# Modelo: {equipamento.get_modelo_display()}
# Gerado pelo painel — aplicar UMA vez. Idempotente em re-execuções.

:log info "DIVSYSTEM bootstrap iniciado"

# 1) Identidade
/system identity set name="{identity}"

# 2) Senha do usuário admin
/user set [find name=admin] password="{nova_senha_admin}"

# 3) Interface WireGuard cliente
/interface wireguard
:if ([:len [find name=wg-divsystem]] = 0) do={{
  add name=wg-divsystem listen-port=13231 private-key="{equipamento.wg_privkey_device}" comment="DIVSYSTEM tunnel"
}} else={{
  set [find name=wg-divsystem] private-key="{equipamento.wg_privkey_device}" comment="DIVSYSTEM tunnel"
}}

# 4) Peer (servidor / hub)
/interface wireguard peers
:if ([:len [find comment="DIVSYSTEM hub"]] = 0) do={{
  add interface=wg-divsystem public-key="{server_pubkey}" \\
      endpoint-address={server_endpoint_host} endpoint-port={server_endpoint_port} \\
      allowed-address=10.10.10.0/24 persistent-keepalive=25s \\
      comment="DIVSYSTEM hub"
}} else={{
  set [find comment="DIVSYSTEM hub"] \\
      public-key="{server_pubkey}" \\
      endpoint-address={server_endpoint_host} endpoint-port={server_endpoint_port} \\
      allowed-address=10.10.10.0/24 persistent-keepalive=25s
}}

# 5) Endereço IP na interface WG
/ip address
:if ([:len [find interface=wg-divsystem]] = 0) do={{
  add address={equipamento.wg_ip}/24 interface=wg-divsystem comment="DIVSYSTEM"
}}

# 6) Lista de endereços para regras de firewall
/ip firewall address-list
:if ([:len [find list=divsystem-mgmt]] = 0) do={{
  add list=divsystem-mgmt address=10.10.10.1 comment="DIVSYSTEM hub"
}}

# 7) Usuário API + grupo restrito
/user group
:if ([:len [find name=divsystem-api]] = 0) do={{
  add name=divsystem-api policy=read,write,api,rest-api,test,!local,!telnet,!ssh,!ftp,!reboot,!password,!web,!sniff,!sensitive,!romon
}}
/user
:if ([:len [find name="{equipamento.api_user}"]] = 0) do={{
  add name="{equipamento.api_user}" group=divsystem-api password="{equipamento.api_password}" address=10.10.10.0/24 comment="DIVSYSTEM API"
}} else={{
  set [find name="{equipamento.api_user}"] group=divsystem-api password="{equipamento.api_password}" address=10.10.10.0/24
}}

# 8) Habilitar www-ssl (REST API HTTPS) — usa cert auto-gerado
/certificate
:if ([:len [find name=divsystem-rest]] = 0) do={{
  add name=divsystem-rest common-name="{identity}" days-valid=3650 key-usage=digital-signature,key-encipherment,tls-server
  sign divsystem-rest
}}
/ip service
set www-ssl certificate=divsystem-rest disabled=no port=443
set www-ssl address=10.10.10.0/24
set api-ssl address=10.10.10.0/24
set api address=10.10.10.0/24
set ssh address=10.10.10.0/24
set winbox address=10.10.10.0/24,192.168.88.0/24
set telnet disabled=yes
set ftp disabled=yes
set www disabled=yes

# 9) Firewall: bloquear gerência vinda da WAN; só permitir vindo da WG
/ip firewall filter
:if ([:len [find comment="DIVSYSTEM allow mgmt from wg"]] = 0) do={{
  add chain=input action=accept in-interface=wg-divsystem comment="DIVSYSTEM allow mgmt from wg" place-before=0
}}

:log info "DIVSYSTEM bootstrap concluído — equipamento {equipamento.pk}"
:put "OK — divsystem bootstrap concluído. WG IP: {equipamento.wg_ip}"
"""
    return dedent(script)
