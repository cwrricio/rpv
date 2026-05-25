# ADR 0004 — Modelo de dados em duas camadas: Raw e Canonical

**Status:** Decidido  
**Data:** 2026-05-11

## Contexto

O sistema coleta dados acadêmicos de múltiplas fontes externas: OpenAlex, ORCID, Crossref e Semantic Scholar. Cada fonte retorna dados em formato e vocabulário próprios. Por exemplo:

- OpenAlex usa `display_name`, `publication_year`, `cited_by_count`, `authorships`.
- Crossref usa `author`, `published`, `is-referenced-by-count`.
- Semantic Scholar usa `name`, `year`, `citationCount`, `authors`.

A questão é: o que salvar no banco de dados?

As alternativas consideradas foram:

1. **Salvar apenas o dado normalizado (canonical)** — menor uso de armazenamento, mas se a normalização estiver errada, os dados originais são perdidos e a reprocessamento é impossível sem chamar a API externa novamente.
2. **Salvar apenas o dado bruto (raw)** — auditável e reprocessável, mas inutilizável diretamente pela aplicação sem transformação em tempo de requisição.
3. **Salvar as duas camadas** — raw como registro histórico e auditável; canonical como dado pronto para uso pela aplicação.

## Decisão

**Duas camadas: Raw e Canonical.**

- **Raw:** dado exatamente como veio da API externa, salvo em `/openalex/{id}/batches/{timestamp}/works` e `/external/{fonte}/{id}/`. Nunca alterado após a coleta.
- **Canonical:** dado normalizado e unificado, salvo em `/autores_flat/{slug}` e `/produtos/{id}`. É o que a interface consome.

## Justificativa

- **Auditabilidade:** é possível rastrear de onde veio cada dado e quando foi coletado.
- **Reprocessamento:** se a lógica de normalização mudar, o canonical pode ser regenerado a partir do raw sem precisar chamar as APIs externas novamente.
- **Fusão de fontes:** o canonical pode agregar dados de múltiplas fontes (OpenAlex + ORCID + Semantic Scholar) sobre o mesmo autor, algo impossível se só o raw fosse guardado.
- **Resiliência:** APIs externas têm rate limits e instabilidades. Ter o raw salvo garante que a coleta não precisa ser refeita para corrigir a normalização.

## Consequências

- O armazenamento é maior do que o necessário para a operação diária — o raw ocupa espaço relevante.
- O pipeline de ingestão tem dois passos obrigatórios: (1) salvar raw, (2) processar e gravar canonical. Isso é feito pelos módulos `ingest/` e `workers/`, respectivamente.
- O raw **nunca deve ser lido diretamente pela interface** — apenas pelo pipeline de processamento. Toda consulta da API HTTP usa o canonical.
- A fronteira entre raw e canonical deve ser mantida clara: qualquer novo campo de API externa vai primeiro para o raw, depois é mapeado para o canonical por um worker.
