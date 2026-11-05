Mundo 1: a prata confiável
Objetivo: provar que as 22 tabelas no Postgres são fiéis à fonte. Ao final, um único comando roda o catálogo de testes a cada carga, guarda o resultado no banco e impede a gold de ser atualizada se algo crítico quebrar.

1.1: Briefing: como se testa dado

 - A diferença entre teste de código e teste de dado esta no resultado. O teste de código confere funções e comportamento do algoritmo, enquanto que o teste de dado está na fonte dos dados, uma tabela 1:1 que tem PK duplicada por exemplo

 - Exemplos de ERRO: PK duplicada, tabela must vazia, erro silencioso. 
 Exemplos de ALERTA: Data desformatada, soma que nao fecha, muitos nulos.

1.2: Tutorial: o teste é uma consulta

 - T-C01: retornou 0 linhas, ou seja,grp_instrumento tem uma linha por nr_grp, como esperado pela premissa P3
 - T-D01: Retornou 4863 linhas, afinal, na fonte dos dados cd_proposta veio com tudo vazio, menos 13 instrumentos que são apenas propostas, nao viraram convenio ainda, então nao tem nr_grp. Realmente cd_proposta deveria ser mais presente, irei conferir com a equipe responsável o porque na fonte dos dados vem errado.
 - T-D02: Retornou as 13 propostas que nao tem nr_grp e tem cd_proposta. 10 com ds_situacao_proposta = PROPOSTA_APROVADA_NV_2_PQ e 3 com ds_situacao_proposta = PROPOSTA_INC_NO_BANCO_DE_PROJ.

 - o WHERE nr_grp IS NOT NULL é necessário no T-C01 porque sem o filtro, o teste acusaria uma duplicidade que não existe dos registros NULL.

 - Escreti o T-D02 conforme indicado no tutorial. Retornou linhas e eu sei o porque, problemas na fonte que terão que ser conferidos com a equipe responsável.