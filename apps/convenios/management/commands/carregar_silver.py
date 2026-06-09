"""
Management command: carregar_silver

Lê o arquivo Silver mais recente de uma fonte e popula o banco
via Django ORM de forma idempotente.

Idempotência:
    Usamos update_or_create(nr_convenio=..., defaults={...}).
    - Se o convênio já existir no banco: atualiza todos os campos.
    - Se não existir: cria.
    Rodar duas vezes produz o mesmo resultado — sem duplicatas.
    O campo `atualizado_em` (auto_now=True) registra quando foi a última carga.

Uso:
    python manage.py carregar_silver convenios
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.convenios.models import Convenio


def _para_date(valor: str) -> date | None:
    """ISO 8601 string → date. Retorna None para campo vazio."""
    return date.fromisoformat(valor) if valor else None


def _para_decimal(valor: str) -> Decimal | None:
    """String com ponto decimal → Decimal. Retorna None para campo vazio."""
    if not valor:
        return None
    try:
        return Decimal(valor)
    except InvalidOperation:
        return None


def _silver_mais_recente(nome_fonte: str) -> Path:
    """Retorna o arquivo Silver mais recente para a fonte."""
    silver_dir = Path(settings.DATA_DIR) / "silver" / nome_fonte
    arquivos = sorted(silver_dir.glob(f"{nome_fonte}_silver_*.csv"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo Silver encontrado em {silver_dir}.\n"
            f"Rode antes: python manage.py rodar_transformacao {nome_fonte}"
        )
    return arquivos[-1]


class Command(BaseCommand):
    help = "Carrega o Silver mais recente de uma fonte no banco de dados (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("fonte", help="Nome da fonte (ex: convenios)")

    def handle(self, *args, **options):
        nome = options["fonte"]

        # Por enquanto só 'convenios' tem model; estrutura já pronta para expansão
        if nome != "convenios":
            raise CommandError(
                f"Fonte '{nome}' não tem model registrado ainda. "
                "Adicione o model e atualize este comando nas próximas fases."
            )

        try:
            silver_path = _silver_mais_recente(nome)
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(f"Carregando Silver: {silver_path.name} ...")

        df = pd.read_csv(silver_path, dtype=str, keep_default_na=False)

        criados = atualizados = erros = 0

        for _, row in df.iterrows():
            nr = row.get("nr_convenio", "").strip()
            if not nr:
                self.stderr.write(f"Linha sem nr_convenio ignorada: {dict(row)}")
                erros += 1
                continue

            try:
                _, criado = Convenio.objects.update_or_create(
                    nr_convenio=nr,
                    defaults={
                        "nr_processo": row.get("nr_processo", ""),
                        "objeto": row.get("objeto", ""),
                        "concedente": row.get("concedente", ""),
                        "convenente": row.get("convenente", ""),
                        "situacao": row.get("situacao", ""),
                        "valor_global": _para_decimal(row.get("valor_global", "")),
                        "data_inicio": _para_date(row.get("data_inicio", "")),
                        "data_termino": _para_date(row.get("data_termino", "")),
                    },
                )
                if criado:
                    criados += 1
                else:
                    atualizados += 1
            except Exception as exc:
                self.stderr.write(f"Erro ao salvar {nr}: {exc}")
                erros += 1

        from apps.dashboard.services import invalidar_cache
        invalidar_cache()

        self.stdout.write(
            self.style.SUCCESS(
                f"Concluido! Criados: {criados} | Atualizados: {atualizados} | Erros: {erros}"
            )
        )
