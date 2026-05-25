# Frente 4 — Camada de Serviços e Testes

**Data:** 2026-05-25
**Branch:** `frente4-emanuel`
**Referências:** `docs/frentes-refatoracao.md` (Frente 4) · `docs/relatorio-refatoracao.md` · `docs/ARCHITECTURE.md`

Documenta tudo que foi implementado na Frente 4: a extração da lógica de
métricas para a camada de serviços e a criação da suíte de testes.

---

## Contexto da branch (importante)

Esta branch contém a **Frente 3** (schemas Pydantic, `lru_cache`,
`response_model`, `services/produtos.py`), mas **não** contém a **Frente 2**
(renomeações e correções). Consequências no código real desta branch:

| Doc da Frente 4 assume | Nesta branch ainda é |
|---|---|
| `functions/repositories/` | `functions/crud/` |
| `functions/common/` | `functions/commom/` (com typo) |
| bug `self._node()` já corrigido (Frente 2.3) | bug ainda presente — **corrigido aqui** (ver abaixo) |

A implementação foi feita contra a estrutura **real** da branch. Quando a
Frente 2 for mergeada, os caminhos `crud/` → `repositories/` e
`commom/` → `common/` mudam, mas o conteúdo dos testes/serviço continua válido
(só os imports acompanham a renomeação).

---

## Resumo das atividades

| # | Atividade | Status | Arquivo(s) |
|---|---|---|---|
| 4.1 | Extrair h-index, h5-index, i10-index e agregação de publicações de `main.py` para `services/analytics.py` | ✅ | `functions/services/analytics.py` |
| 4.2 | Handler `/autores/{id}/metrics` delega para `services/analytics.compute_author_metrics()` | ✅ | `functions/main.py` |
| 4.3 | Testes unitários para `services/analytics.py` (sem Firebase) | ✅ | `tests/test_analytics.py` |
| 4.4 | Testes de rota para `api_routes/docentes.py` com `TestClient` | ✅ | `tests/test_docentes.py` |
| 4.5 | Testes unitários Pydantic para `domain/schemas.py` | ✅ | `tests/test_schemas.py` |
| 4.6 | Testes de integração para `BaseCRUD` (create/list/get/update/delete) | ✅ | `tests/test_base_crud.py` |
| — | **Pré-requisito:** correção do bug `self._node()` → `self.ref()` (Frente 2.3) | ✅ | `functions/crud/docente_crud.py` |

---

## 4.1 — `services/analytics.py`

`services/analytics.py` estava vazio (`# TODO: implementar`). A lógica de
agregação de métricas, que vivia inteiramente no handler `main.py` (linhas
~100–206), foi movida para lá como **funções puras** — recebem o nó
`autores_flat/{id}` (um `dict` já lido do banco) e não tocam o Firebase, o que
as torna testáveis sem emulador nem rede.

Funções expostas:

- `extract_works(node)` — normaliza `works` (mapa **ou** lista) para uma lista
  de obras, ignorando a sentinela `"_"` e valores não-`dict`.
- `compute_h_index(citations)` — maior `h` tal que `h` obras têm ≥ `h` citações.
- `compute_i10_index(citations, threshold=10)` — nº de obras com ≥ 10 citações.
- `compute_h5_index(works, reference_year=None, window=5)` — h-index restrito às
  obras dos últimos `window` anos. **Novo:** não existia no handler original.
- `compute_author_metrics(author_id, node, ...)` — orquestra tudo e devolve o
  dicionário de resposta.

**Métricas adicionadas nesta frente:** o handler original calculava apenas
`h_index`. A Frente 4.1 pede h-index, **h5-index** e **i10-index** — os dois
últimos foram implementados e passaram a integrar a resposta da rota.

### Definição do h5-index (decisão de projeto)

A janela é `[reference_year - window + 1, reference_year]`. Por padrão,
`reference_year` é o **maior ano presente nas obras do autor** (determinístico —
não depende do relógio do servidor, o que mantém o cálculo estável e os testes
reprodutíveis). É possível passar `reference_year` explicitamente quando se quer
fixar o ano (ex.: alinhar ao "últimos 5 anos completos" do Google Scholar).

---

## 4.2 — Handler delega para o serviço

`GET /autores/{id}/metrics` em `main.py` foi reduzido à sua única
responsabilidade: ler o nó do banco, devolver 404 se vazio e delegar:

```python
@app.get("/autores/{author_id}/metrics", ...)
def author_metrics(author_id: str):
    try:
        node = _rtdb_get(f"autores_flat/{author_id}")
        if not node:
            raise HTTPException(status_code=404, detail="Autor não encontrado")
        return compute_author_metrics(author_id, node)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RTDB error: {e}")
```

Foram removidas ~90 linhas de lógica de negócio do handler e o import agora
ocioso de `from collections import Counter` no topo de `main.py`.

---

## Pré-requisito: correção do bug crítico `find_by_orcid`

O teste 4.4 exige verificar que `DocenteCRUD.find_by_orcid` **não lança
`AttributeError`**. Na branch, o método ainda chamava `self._node()`, que não
existe em `BaseCRUD` (só existe `self.ref()`) — o bug crítico descrito no
relatório de refatoração e atribuído à Frente 2.3.

Como sem a correção o teste 4.4 falharia (e a meta era "tudo funcionando"), a
correção de **uma linha** foi aplicada aqui e está sinalizada no código como
dependência da Frente 2.3:

```python
# functions/crud/docente_crud.py
node = self.ref()  # antes: self._node()  -> AttributeError em produção
```

---

## 4.3–4.6 — Suíte de testes

Os testes ficam em `tests/` (raiz do projeto). Infraestrutura de suporte:

- `conftest.py` (raiz) — insere a raiz no `sys.path` e define `PROJECT_ID`/
  `RTDB_URL` para que `config.settings` importe sem `.env` válido.
- `pytest.ini` — `testpaths = tests` e silencia warnings de depreciação ruidosos
  (Pydantic v1 `validator`, `on_event` do FastAPI).

| Arquivo | Frente | O que cobre |
|---|---|---|
| `tests/test_analytics.py` | 4.3 | h-index, i10-index, h5-index com citações conhecidas; `extract_works`; agregação completa de `compute_author_metrics`; nó vazio; limite de `sample_publications`. Sem Firebase. |
| `tests/test_docentes.py` | 4.4 | Rotas via `TestClient` com CRUD fake injetado por `dependency_overrides`: 201 na criação, **422** em `tipo` inválido (validação Pydantic), normalização de caixa, 404 em obter/atualizar/remover inexistente, 204 na remoção. Mais: teste direto de `find_by_orcid` (usa `self.ref()`, sem `AttributeError`) e de `create` rejeitando `tipo` inválido. |
| `tests/test_schemas.py` | 4.5 | Normalização e **rejeição de `TipoDocente`/`StatusPesquisa` inválidos**, `tipo` vazio → `None`, `to_payload()` excluindo `None`/unset, `DocenteOut` exigindo `id`, campo extra permitido. |
| `tests/test_base_crud.py` | 4.6 | Ciclo create/list/get/update/delete de `BaseCRUD` contra um **RTDB fake em memória** (sempre roda) + teste contra **emulador Firebase real** (opt-in via `FIREBASE_DATABASE_EMULATOR_HOST`, pulado por padrão). |

### Decisões de teste

- **Sem importar `main.py`** nos testes de rota: `main.py` chama `init_firebase()`
  no import. Os testes de rota montam uma `FastAPI()` mínima que inclui apenas o
  `router` de docentes e sobrescrevem a dependência `crud` com um fake em memória.
- **`find_by_orcid`** não tem endpoint (o router não o expõe), então é testado
  diretamente na classe com um `ref()` mockado — é onde o `AttributeError` do
  bug apareceria.
- **Emulador opcional**: a Frente 4.6 pede "emulador Firebase". Para a suíte ser
  sempre verde sem infraestrutura, o ciclo CRUD roda contra um fake em memória
  que imita a API de `db.Reference`; o teste real com emulador existe e roda
  quando `FIREBASE_DATABASE_EMULATOR_HOST` estiver definido.

### Resultado

```
54 passed, 1 skipped in 0.40s
```

(O único `skipped` é o teste de emulador, por design.)

Como rodar:

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Execução end-to-end e conferência do README

Fluxo do README exercitado (backend):

1. `python -m venv` + `pip install -r requirements.txt` → OK.
2. `uvicorn functions.main:app --host 127.0.0.1 --port <p>` → **sobe normalmente**.
3. Verificações do README:
   - `GET /health` → `200 {"ok": true}` ✅
   - `GET /` → `200 {"status": "API rodando 🚀"}` ✅
   - `GET /docs` (Swagger) → `200` ✅
   - `GET /openapi.json` → rota `/autores/{author_id}/metrics` presente ✅
4. `GET /docentes` (toca o DB) → `500` com
   `File C:\Users\ResTIC16\...\service-account.json was not found.`

### Achados sobre o README / fluxo

| # | Achado | Severidade | Ação tomada |
|---|---|---|---|
| 1 | README cita "existe um `.env.example` para referência", mas o arquivo **não existia** | Média | **Criado `.env.example`** (portável, sem caminho Windows) |
| 2 | `.env` versionado aponta `GOOGLE_APPLICATION_CREDENTIALS` para um caminho Windows (`C:\Users\ResTIC16\...`) inexistente em outras máquinas → todo endpoint que toca o DB retorna 500 | Alta | Documentado. Correção definitiva é da Frente 1 (não comitar `.env`); o `.env.example` criado mostra o formato correto |
| 3 | README manda `python -m venv venv`, mas o repo versiona um `.venv/` (que estava **vazio/quebrado**) | Baixa | Recriado o virtualenv localmente; nomenclatura é cosmética |
| 4 | README não documentava como rodar testes nem listava `pytest`/`httpx` | Média (Frente 4) | **Adicionada seção "Testes"** ao README e criado `requirements-dev.txt` |

**Conclusão:** o backend sobe e as rotas que não dependem do banco respondem
conforme o README. A inicialização do Firebase é preguiçosa, então a falta de
credencial válida só quebra endpoints que acessam o RTDB — comportamento
coerente com a seção "Credenciais"/"Troubleshooting". As lacunas do README
(`.env.example`, seção de testes) foram corrigidas nesta frente.

---

## Arquivos criados/alterados

**Criados**
- `functions/services/analytics.py` (era stub `# TODO`)
- `tests/test_analytics.py`, `tests/test_docentes.py`, `tests/test_schemas.py`, `tests/test_base_crud.py`
- `conftest.py`, `pytest.ini`
- `.env.example`, `requirements-dev.txt`
- `docs/frente 4.md` (este arquivo)

**Alterados**
- `functions/main.py` — handler delega ao serviço; remoção de lógica e import ocioso
- `functions/crud/docente_crud.py` — correção `self._node()` → `self.ref()`
- `README.md` — seção "Testes"
- `docs/frentes-refatoracao.md` — Frente 4 marcada como concluída
