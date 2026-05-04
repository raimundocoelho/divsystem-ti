from rest_framework import serializers

from .models import AgentHeartbeat, AgentToken, RemoteCommand


class HeartbeatInputSerializer(serializers.Serializer):
    machine_id = serializers.CharField(max_length=255)
    agent_version = serializers.CharField(max_length=20, required=False, allow_blank=True)
    hardware = serializers.JSONField(required=False, allow_null=True)
    network = serializers.JSONField(required=False, allow_null=True)
    system = serializers.JSONField(required=False, allow_null=True)
    software = serializers.JSONField(required=False, allow_null=True)
    peripherals = serializers.JSONField(required=False, allow_null=True)
    alerts = serializers.JSONField(required=False, allow_null=True)
    collected_at = serializers.DateTimeField(required=False, allow_null=True)
    hostname = serializers.CharField(max_length=255, required=False, allow_blank=True)


class EnrollSerializer(serializers.Serializer):
    enroll_code = serializers.CharField(required=False, allow_blank=True)
    master_key = serializers.CharField(required=False, allow_blank=True)
    hostname = serializers.CharField(max_length=255, required=False, allow_blank=True)
    machine_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    secretaria_id = serializers.IntegerField(required=False, allow_null=True)
    setor_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)


class CommandResultSerializer(serializers.Serializer):
    command_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["running", "success", "completed", "failed"])
    # O agente C# 5.2.x sempre envia AMBOS os campos: em Ok(out), error=null; em
    # Fail(err), output=null. Sem allow_null=True o DRF retorna 400 e o cmd
    # nunca completa. allow_blank cobre o caso de string vazia.
    output = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    error = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class AgentTokenSerializer(serializers.ModelSerializer):
    online_status = serializers.CharField(read_only=True)
    online_status_label = serializers.SerializerMethodField()

    class Meta:
        model = AgentToken
        fields = (
            "id", "name", "hostname", "machine_id", "agent_version",
            "secretaria", "setor", "active", "is_canary",
            "last_seen_at", "last_ping_at",
            "online_status", "online_status_label",
            "created_at", "updated_at",
        )
        read_only_fields = ("token", "machine_id", "last_seen_at", "last_ping_at")

    def get_online_status_label(self, obj):
        return obj.online_status_label()


class RemoteCommandSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="command_label", read_only=True)

    class Meta:
        model = RemoteCommand
        fields = (
            "id", "command", "label", "payload", "status",
            "output", "error", "created_at", "executed_at", "completed_at",
        )
        read_only_fields = ("status", "output", "error", "executed_at", "completed_at")
