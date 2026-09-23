"""
Migração manual: substitui o schema do Convenio da Fase 4 pelo schema
alinhado à Silver dcgce_convenios (fonte SIGCON-MG / Business Objects).

Estratégia DeleteModel + CreateModel: a estrutura mudou completamente
(campos novos, campos antigos removidos, tipos diferentes), tornando
o diff incremental mais confuso do que um recomeço limpo.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="Convenio"),
        migrations.CreateModel(
            name="Convenio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("convenio_codigo", models.CharField(db_index=True, max_length=50, verbose_name="Código do Convênio")),
                ("convenio_numero_sequencial_siafi", models.CharField(blank=True, max_length=50, null=True, verbose_name="Nº Sequencial SIAFI")),
                ("unidade_orcamentaria_codigo", models.CharField(blank=True, max_length=20, null=True, verbose_name="Cód. Unidade Orçamentária")),
                ("situacao", models.CharField(blank=True, max_length=100, null=True, verbose_name="Situação")),
                ("data_inicio_vigencia", models.DateField(blank=True, null=True, verbose_name="Início de Vigência")),
                ("data_termino_vigencia", models.DateField(blank=True, null=True, verbose_name="Término de Vigência")),
                ("data_real_convenio", models.DateField(blank=True, null=True, verbose_name="Data Real do Convênio")),
                ("valor_inicial_concedente_contratado", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name="Valor Inicial Concedente")),
                ("valor_total_aditado_concedente_contratado", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name="Valor Total Aditado Concedente")),
                ("valor_concedente", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name="Valor Concedente")),
                ("valor_inicial_proponente_contratado", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name="Valor Inicial Proponente")),
                ("valor_total_aditado_proponente_contratado", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name="Valor Total Aditado Proponente")),
                ("valor_proponente", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name="Valor Proponente")),
                ("valor_total_convenio", models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name="Valor Total do Convênio")),
                ("atualizado_em", models.DateTimeField(auto_now=True, verbose_name="Atualizado em")),
            ],
            options={
                "verbose_name": "Convênio",
                "verbose_name_plural": "Convênios",
                "ordering": ["-data_inicio_vigencia"],
                "indexes": [
                    models.Index(fields=["situacao"], name="convenios_situacao_idx"),
                    models.Index(fields=["data_inicio_vigencia"], name="convenios_data_inicio_idx"),
                ],
            },
        ),
    ]
