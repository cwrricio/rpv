# Mudanças

Resumo do que foi feito na Frente 2:

- Renomeei `functions/commom` para `functions/common`.
- Renomeei `functions/crud` para `functions/repositories`.
- Atualizei os imports para usar os novos nomes.
- Centralizei o acesso ao Firebase em `functions/common/dbref.py`.
- Corrigi o bug em `DocenteCRUD.find_by_orcid`, trocando `self._node()` por `self.ref()`.
- Troquei o set local `TIPOS_VALIDOS` pelo enum `TipoDocente`.
- Atualizei arquivos auxiliares como `setup.py` e `packages.puml`.
