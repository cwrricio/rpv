# ADR 0006 - Autenticacao independente de provedor

Data: 2026-06-22
Status: Proposto, aguardando decisao de produto

## Contexto

A issue SSQM #14 pede uma estrategia de autenticacao propria caso login real
seja necessario. O objetivo de soberania e evitar que a identidade dos usuarios
fique acoplada a Google/Firebase.

O estado atual do codigo nao tem autenticacao real obrigatoria:

- O frontend possui tela de login e `AuthProvider`, mas o cliente Firebase esta
  stubado.
- O backend nao protege rotas com JWT.
- A documentacao antiga citava Firebase Auth, mas isso nao esta implementado.

## Requisitos de produto ainda pendentes

- Quais perfis existem: administrador, coordenador, docente, discente, leitura?
- Quais rotas precisam autenticacao e quais devem continuar publicas?
- E necessario SSO institucional?
- E necessario auto-cadastro, convite, recuperacao de senha e MFA?
- Quais eventos precisam auditoria?
- Existe requisito de dados sensiveis ou LGPD que exija sessao curta/revogacao?

## Opcoes consideradas

### Manter sem login real por enquanto

Vantagens:

- Preserva o comportamento atual.
- Nao adiciona dependencia operacional.
- Evita uma decisao prematura antes dos requisitos.

Desvantagens:

- Nao atende cenarios reais de multiusuario ou dados restritos.

### Firebase Auth

Vantagens:

- Integracao simples com o ecossistema Firebase.
- SDKs maduros para frontend.

Desvantagens:

- Reintroduz lock-in Google/Firebase justamente na frente DEP-03.
- Exige verificacao via Firebase Admin SDK ou chaves do provedor.
- Contraria a diretriz de isolar Firebase como legado.

### Keycloak self-hosted via OIDC

Vantagens:

- Padrao aberto OIDC/OAuth2.
- Pode rodar em Docker e em infraestrutura propria.
- Permite trocar o provedor mantendo a porta da aplicacao.
- Suporta realm, roles, grupos, SSO e MFA.

Desvantagens:

- Custo operacional maior.
- Exige governanca de usuarios, backup e atualizacoes.

### Provedor OIDC gerenciado

Exemplos: Auth0, Okta, Azure AD, Google Identity.

Vantagens:

- Menor operacao interna.
- Bons recursos de seguranca e auditoria.

Desvantagens:

- Lock-in comercial/operacional muda de lugar.
- Custos e limites podem crescer.
- Pode nao cumprir soberania se a identidade ficar fora da organizacao.

## Decisao

Por enquanto, manter `AUTH_PROVIDER=disabled` e `AUTH_REQUIRED=false` como
padrao. Isso representa fielmente o estado atual do produto e evita quebrar
rotas existentes.

Se o produto aprovar login real, usar uma estrategia OIDC independente de
fornecedor. A opcao preferencial de soberania e Keycloak self-hosted; provedores
gerenciados podem ser avaliados se a operacao interna for um risco maior que o
lock-in.

Firebase Auth nao deve ser o caminho canonico para login novo. Se ainda for
necessario para compatibilidade, deve ficar isolado em um adaptador legado da
porta de autenticacao.

## Implementacao inicial

- `functions/auth/ports.py` define `AuthProviderPort` e `AuthenticatedUser`.
- `functions/auth/providers.py` fornece `DisabledAuthProvider` e placeholder OIDC
  que falha fechado ate existir verificacao JWT/JWKS real.
- `functions/auth/dependencies.py` contem dependencias FastAPI reutilizaveis.
- `functions/api_routes/auth.py` expoe `/auth/config` e `/auth/me` para
  diagnostico sem segredos.

## Proximos passos para POC aprovada

1. Confirmar requisitos reais de perfis, rotas protegidas, SSO, MFA e auditoria.
2. Escolher biblioteca de verificacao OIDC/JWKS (`authlib`, `python-jose` ou
   equivalente) e adicionar testes de tokens validos/invalidos.
3. Subir Keycloak no `docker-compose.yml` somente se a decisao de produto for
   favoravel.
4. Mapear claims OIDC para roles internas do Poshboard.
5. Proteger uma rota de baixo risco com `required_user` e validar o fluxo ponta
   a ponta.
