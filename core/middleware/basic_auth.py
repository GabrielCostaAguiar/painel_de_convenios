"""
Middleware de Basic Auth para o modo de compartilhamento temporário
(MODO_COMPARTILHAR=1) — ver COMPARTILHAR.md.

Só é inserido em MIDDLEWARE quando essa env var está ativa; o settings.py
decide isso, esta classe não lê MODO_COMPARTILHAR.
"""

import base64
import hmac
import os

from django.http import HttpResponse


class ShareBasicAuthMiddleware:
    """
    Exige usuário/senha (SHARE_USER / SHARE_PASSWORD) via Basic Auth em
    toda requisição. Se SHARE_IPS estiver definida (IPs separados por
    vírgula), bloqueia quem não estiver na lista — lida via
    X-Forwarded-For, já que o túnel faz REMOTE_ADDR virar localhost.
    """

    REALM = "Painel de Convenios"

    def __init__(self, get_response):
        self.get_response = get_response
        self.share_user = os.environ.get("SHARE_USER", "")
        self.share_password = os.environ.get("SHARE_PASSWORD", "")
        ips = os.environ.get("SHARE_IPS", "").strip()
        self.allowed_ips = {ip.strip() for ip in ips.split(",") if ip.strip()} or None

    def __call__(self, request):
        if self.allowed_ips is not None and self._client_ip(request) not in self.allowed_ips:
            return HttpResponse("Acesso bloqueado para este IP.", status=403)

        if not self._autenticado(request):
            response = HttpResponse("Autenticação necessária.", status=401)
            response["WWW-Authenticate"] = f'Basic realm="{self.REALM}"'
            return response

        return self.get_response(request)

    def _client_ip(self, request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    def _autenticado(self, request) -> bool:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Basic "):
            return False
        try:
            usuario, _, senha = base64.b64decode(header[6:]).decode("utf-8").partition(":")
        except (ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(usuario, self.share_user) and hmac.compare_digest(senha, self.share_password)
