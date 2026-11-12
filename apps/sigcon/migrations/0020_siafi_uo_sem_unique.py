"""
Remove unique=True de SigconConvenio.siafi_uo. O grão (1 linha por siafi_uo) é
garantido pelo teste T-C01 do catálogo de validação, em ERRO, e não por
constraint: uma duplicata na fonte deve ser reportada, não derrubar a carga.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0019_remove_indice_duplicado_cd_plano_trabalho"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sigconconvenio",
            name="siafi_uo",
            field=models.CharField(blank=True, db_index=True, max_length=30, null=True),
        ),
    ]
