"""
Models de fontes externas ao SIGCON-MG.

Hoje só ControleSEI, a planilha interna de controle do nº SEI por convênio.
"""

from django.db import models


# ---------------------------------------------------------------------------
# ControleSEI — planilha interna de controle do nº SEI por convênio
# ---------------------------------------------------------------------------

class ControleSEI(models.Model):
    """
    Fonte: data/silver/controle_sei.parquet
    Carga: full refresh via carregar_controle_sei().

    Chave de ligação principal:
      no_siafi_sigcon → Convenio.convenio_numero_sequencial_siafi  (SIAFI puro, não siafi_uo)
    Chave secundária (SICONV):
      no_proposta_siconv → ConvenioIntegrado.codigo_siconv

    Atenção: o Parquet Silver usa nomes no_siafi_(sigcon) e no_proposta_(siconv)
    com parênteses — o loader mapeia para estes campos sem parênteses.
    """

    no_sei = models.CharField(
        "Nº SEI", max_length=100, db_index=True, null=True, blank=True,
    )
    no_siafi_sigcon = models.CharField(
        "Nº SIAFI (SIGCON)", max_length=50, db_index=True, null=True, blank=True,
    )
    no_proposta_siconv = models.CharField(
        "Nº Proposta (SICONV)", max_length=50, null=True, blank=True,
    )

    # --- controle de carga ---
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Controle SEI"
        verbose_name_plural = "Controles SEI"
        indexes = [
            models.Index(fields=["no_siafi_sigcon"], name="sei_siafi_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.no_sei or '—'} → SIAFI {self.no_siafi_sigcon or '—'}"
