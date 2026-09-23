"""
Models da app convenios, agrupados por domínio.

Era um único models.py de ~1360 linhas com 24 models. O Django aceita `models`
como pacote sem nenhuma cerimônia: o ORM identifica um model por app_label +
nome da classe, nunca pelo arquivo onde ele foi declarado — por isso a divisão
não muda nome de tabela, não mexe no schema e não gera migração.

Os arquivos:
  sigcon.py    — tabelas do SIGCON-MG (Convenio + auxiliares)
  codigos.py   — tabelas de mapeamento de códigos entre entidades
  gold.py      — camada Gold (ConvenioIntegrado)
  externos.py  — fontes externas ao SIGCON-MG (ControleSEI)
  grp.py       — tabelas do GRP (em teste)

Tudo é reexportado aqui, então `from apps.convenios.models import Convenio`
continua funcionando igual em todo o projeto — nenhum import externo mudou.
"""

from .codigos import (
    CodigoConvenio,
    CodigoDeclaracaoContrapartida,
    CodigoPlanoTrabalho,
    CodigoTermoAditivo,
)
from .externos import ControleSEI
from .gold import ConvenioIntegrado
from .grp import (
    CronogramaDesembolsoGrp,
    DadosGrp,
    EsferaGrp,
    PlanoAplicacaoGrp,
    PlanoAplicacaoGrpDetalhes,
    RecursosConcedenteGrp,
    RecursosContrapartidaGrp,
)
from .sigcon import (
    Convenio,
    ConvenioGeral,
    CronogramaDesembolso,
    DeclaracaoContrapartida,
    Esfera,
    NtEmenda,
    PlanoAplicacao,
    PlanoTrabalho,
    ProrrogacaoOficio,
    TermoAditivo,
    UnidadesExecutoras,
)

__all__ = [
    # sigcon
    "Convenio",
    "ConvenioGeral",
    "PlanoTrabalho",
    "CronogramaDesembolso",
    "PlanoAplicacao",
    "TermoAditivo",
    "DeclaracaoContrapartida",
    "ProrrogacaoOficio",
    "NtEmenda",
    "Esfera",
    "UnidadesExecutoras",
    # codigos
    "CodigoConvenio",
    "CodigoPlanoTrabalho",
    "CodigoTermoAditivo",
    "CodigoDeclaracaoContrapartida",
    # gold
    "ConvenioIntegrado",
    # externos
    "ControleSEI",
    # grp
    "DadosGrp",
    "CronogramaDesembolsoGrp",
    "RecursosContrapartidaGrp",
    "RecursosConcedenteGrp",
    "PlanoAplicacaoGrp",
    "PlanoAplicacaoGrpDetalhes",
    "EsferaGrp",
]
