# Modelo de Dados Canônico — Poshboard (SSQM)

Mapa dos nós do RTDB e do modelo canônico usado pela camada de portas/adaptadores
(`functions/repositories/ports.py`). Cada nó é uma **coleção** (`path_root`),
com itens identificados por `id` string e corpo em JSON.

## Coleções (nós RTDB → coleções StoragePort)

| Coleção (`path_root`) | Origem (repository) | Conteúdo |
|---|---|---|
| `autores` | `AutorCRUD` | Autores/pesquisadores cadastrados. |
| `autores_flat` | proxy `main.py` / ingest | Visão achatada de autores com obras (`works`) — usada pelo frontend. |
| `produtos` | `ProdutoCRUD` | Produções bibliográficas (artigos, capítulos, etc.); valida DOI. |
| `veiculos` | `VeiculoCRUD` | Veículos de publicação; valida ISSN; carrega Qualis. |
| `docentes` | `DocenteCRUD` | Docentes (PERMANENTE/COLABORADOR/VISITANTE); indexável por `orcid`. |
| `discentes` | `DiscenteCRUD` | Discentes; `status` default `ATIVO`. |
| `linhas` | `LinhaCRUD` | Linhas de pesquisa. |
| `projetos` | `ProjetoCRUD` | Projetos de pesquisa. |
| `pesquisas` | `PesquisaCRUD` / `PesquisaService` | Pesquisas/orientações ligando projeto, linha, orientador e discente. |

## Contrato StoragePort

Operações por coleção: `create / list / get / update / delete`
(ver `functions/repositories/ports.py`). Implementações:

- `FirebaseRTDBAdapter` — legado, sobre o RTDB.
- `PostgresAdapter` — tabela genérica `kv_store(collection, id, data JSON)`,
  paridade nó-a-nó para migração incremental.

## Dívidas de migração (queries fora do StoragePort)

Consultas específicas do RTDB que ainda usam o escape hatch `BaseCRUD.ref()` /
`FirebaseRTDBAdapter.raw_ref()` e precisam ser portadas antes de desligar o Firebase:

| Local | Query | A portar para |
|---|---|---|
| `DocenteCRUD.find_by_orcid` | `order_by_child("orcid").equal_to(...)` | filtro `WHERE data->>'orcid' = ...` no Postgres. |
| `PesquisaService.listar` | `order_by_child("status").equal_to(...)` | filtro por `status` + ordenação por título. |

## Ingestão (NÃO muda)

A forma de obter dados de trabalhos/produção acadêmica permanece via APIs
externas (OpenAlex, ORCID, Crossref, Semantic Scholar) em `functions/ingest/`.
A migração de banco **não** altera esse fluxo de coleta.
