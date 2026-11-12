"""
cd_plano_trabalho de SigconPlanoTrabalho já tem db_index=True no campo (índice
sigcon_plano_trabalho_cd_plano_trabalho_*). O Meta.indexes repetia o mesmo índice
com outro nome (idx_cd_plano_trabalho): fica só o do campo.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "convenios",
            "0018_remove_sigconplanotrabalho_idx_ds_caracteristica_contrapartida",
        ),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="sigconplanotrabalho",
            name="idx_cd_plano_trabalho",
        ),
    ]
