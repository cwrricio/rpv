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

Operações por coleção: `create / upsert / list / get / update / delete`
(ver `functions/repositories/ports.py`). Implementações:

- `FirebaseRTDBAdapter` — legado, sobre o RTDB.
- `PostgresAdapter` — tabela genérica `kv_store(collection, id, data JSON)`,
  paridade nó-a-nó para migração incremental.

`upsert(path_root, id, obj)` existe para fluxos de migracao/backfill: preserva
o id legado exportado do RTDB e substitui o payload daquele item. O CRUD da API
continua usando `create`, que gera id novo no adaptador ativo.

## Migracao RTDB -> PostgreSQL (issue #7)

Fonte esperada: JSONs gerados por `scripts/export_rtdb.py`, no formato
`exports/<timestamp>/<colecao>.json`.

Fluxo recomendado:

```bash
# 1) Validar o export sem escrever no banco
python scripts/migrate_rtdb_to_postgres.py --source exports/20260622T000000Z

# 2) Aplicar no PostgreSQL preservando ids RTDB
python scripts/migrate_rtdb_to_postgres.py \
  --source exports/20260622T000000Z \
  --database-url postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard \
  --apply

# 3) Reverter usando o manifesto gerado, se necessario
python scripts/migrate_rtdb_to_postgres.py \
  --database-url postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard \
  --rollback exports/20260622T000000Z/migration_rollback_<timestamp>.json
```

Use `--replace` apenas em janela controlada: ele remove ids extras nas colecoes
migradas para espelhar exatamente o export, mas o manifesto tambem permite
restaurar esses registros.

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
