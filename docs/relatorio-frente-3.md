# Relatório da Frente 3 - Qualidade FastAPI

Data: 2026-05-25  
Escopo: refatoração apenas dos itens documentados para a Frente 3.

## Objetivo

A Frente 3 tinha como objetivo modernizar a camada FastAPI nas rotas e dependências, melhorando validação de entrada, contrato OpenAPI/Swagger e organização das instâncias de CRUD. As mudanças foram feitas sem aplicar as renomeações da Frente 2, porque o repositório ainda usa `functions/crud` e `functions/commom`.

## O que foi alterado

### 1. Schemas Pydantic criados

Arquivo criado: `functions/domain/schemas.py`

Foram criados os modelos:

- `DocenteCreate`
- `DocenteOut`
- `DiscenteCreate`
- `DiscenteOut`
- `ProjetoCreate`
- `ProjetoOut`

Como foi feito:

- Os schemas herdam de uma base comum que aceita campos extras, preservando compatibilidade com os formatos já usados pelo frontend e pelo banco.
- `DocenteCreate` e `DocenteOut` usam o enum `TipoDocente` de `functions/domain/types.py`.
- `ProjetoCreate` e `ProjetoOut` usam o enum `StatusPesquisa` quando o campo `status` é enviado.
- Os valores de enum são normalizados para maiúsculas antes da validação. Exemplo: `permanente` vira `PERMANENTE`.
- Foi criado o método `to_payload()` para converter o modelo Pydantic em `dict` antes de enviar ao CRUD.

### 2. Rotas de Docentes, Discentes e Projetos tipadas

Arquivos alterados:

- `functions/api_routes/docentes.py`
- `functions/api_routes/discentes.py`
- `functions/api_routes/projetos.py`

Como foi feito:

- Os parâmetros `body: dict` foram substituídos por modelos Pydantic:
  - Docentes usam `DocenteCreate`.
  - Discentes usam `DiscenteCreate`.
  - Projetos usam `ProjetoCreate`.
- Antes de chamar `create()` ou `update()`, a rota usa `body.to_payload()` para entregar um dicionário limpo ao CRUD.
- Foram adicionados `response_model` nos endpoints de criação, listagem, busca e atualização.
- Os endpoints de remoção receberam `response_model=None`, porque retornam HTTP 204 sem corpo.

Resultado:

- O FastAPI passa a validar o corpo das requisições antes de chegar ao CRUD.
- O Swagger/OpenAPI passa a documentar melhor os contratos dessas três entidades.
- Valores inválidos de `TipoDocente` agora são rejeitados pela camada Pydantic.

### 3. Dependências de CRUD com `lru_cache`

Arquivos alterados:

- `functions/api_routes/autores.py`
- `functions/api_routes/docentes.py`
- `functions/api_routes/discentes.py`
- `functions/api_routes/linhas.py`
- `functions/api_routes/pesquisas.py`
- `functions/api_routes/produtos.py`
- `functions/api_routes/projetos.py`
- `functions/api_routes/veiculos.py`

Como foi feito:

- O padrão antigo `_crud = None` com `global _crud` foi removido.
- Cada arquivo passou a usar uma função `crud()` decorada com `@lru_cache`.

Antes:

```python
_crud = None

def crud():
    global _crud
    if _crud is None:
        _crud = DocenteCRUD()
    return _crud
```

Depois:

```python
@lru_cache
def crud() -> DocenteCRUD:
    return DocenteCRUD()
```

Resultado:

- A instância continua sendo reutilizada.
- O estado global mutável explícito sai das rotas.
- O padrão fica mais simples e mais aderente ao FastAPI.

### 4. Ranking de produtos movido para service

Arquivos alterados/criados:

- `functions/api_routes/produtos.py`
- `functions/services/produtos.py`

Como foi feito:

- A regra de cálculo do endpoint `GET /produtos/ranking` foi extraída para `build_author_product_ranking()`.
- O handler da rota agora apenas chama o service.
- O acesso ao Firebase saiu do handler.
- A lógica preserva o comportamento anterior:
  - Primeiro tenta contar autores vinculados a docentes pelo nó `autores`.
  - Se não houver dados ou se a leitura falhar, faz fallback contando autores diretamente nos produtos.

Resultado:

- A rota ficou fina, somente orquestrando a requisição.
- A regra de ranking ficou em `services/`, seguindo a separação de responsabilidades documentada.

### 5. Imports de `HTTPException` consolidados

Arquivo alterado:

- `functions/main.py`

Como foi feito:

- Foram removidos imports internos de `HTTPException` dentro de funções.
- O arquivo já importava `HTTPException` no topo, então as funções passaram a reutilizar esse import.

Resultado:

- Menos repetição.
- Imports mais previsíveis e centralizados.

## Validação realizada

Comandos executados:

```bash
python -m py_compile functions/domain/schemas.py functions/services/produtos.py functions/api_routes/docentes.py functions/api_routes/discentes.py functions/api_routes/projetos.py functions/api_routes/produtos.py functions/api_routes/autores.py functions/api_routes/linhas.py functions/api_routes/pesquisas.py functions/api_routes/veiculos.py functions/main.py
```

Resultado: compilação sintática concluída sem erros.

Também foram feitas validações pontuais:

- `DocenteCreate(tipo="permanente")` gera payload com `PERMANENTE`.
- `ProjetoCreate(status="em_andamento")` gera payload com `EM_ANDAMENTO`.
- `DocenteCreate(tipo="INVALIDO")` gera `ValidationError`.
- O fallback do ranking por produtos retorna a lista ordenada por quantidade.

Observação de ambiente:

- A importação completa das rotas com FastAPI não pôde ser validada no Python global instalado, porque o ambiente local está com combinação incompatível de Python 3.14, FastAPI/Pydantic e sem `firebase_admin` disponível globalmente. Isso não altera as mudanças de código; o `requirements.txt` do projeto especifica as dependências esperadas.

## Arquivos impactados

- `functions/domain/schemas.py`
- `functions/services/produtos.py`
- `functions/api_routes/autores.py`
- `functions/api_routes/docentes.py`
- `functions/api_routes/discentes.py`
- `functions/api_routes/linhas.py`
- `functions/api_routes/pesquisas.py`
- `functions/api_routes/produtos.py`
- `functions/api_routes/projetos.py`
- `functions/api_routes/veiculos.py`
- `functions/main.py`

## Resumo para apresentação

A Frente 3 melhorou a qualidade da camada FastAPI sem mudar paths, métodos HTTP ou a estrutura principal do projeto. As rotas principais de Docentes, Discentes e Projetos agora validam entrada com Pydantic e declaram modelos de resposta. O padrão de singleton manual nas rotas foi substituído por `lru_cache`, reduzindo estado global mutável. A lógica de ranking de produtos foi retirada do handler e movida para `services/`, mantendo o comportamento anterior com fallback. Por fim, os imports de `HTTPException` foram consolidados em `main.py`.
