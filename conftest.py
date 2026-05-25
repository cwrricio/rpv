"""Configuração compartilhada de testes (raiz do projeto).

Fica na raiz para que o pytest insira o diretório do projeto em ``sys.path`` e
os pacotes ``functions`` e ``config`` sejam importáveis pelos testes em
``tests/``. Também define variáveis de ambiente mínimas para que
``config.settings`` possa ser importado sem um ``.env`` válido — nenhum teste
unitário toca o Firebase de verdade.
"""

import os
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Settings() (pydantic-settings) exige PROJECT_ID e RTDB_URL no import.
os.environ.setdefault("PROJECT_ID", "test-project")
os.environ.setdefault("RTDB_URL", "https://test-project-default-rtdb.firebaseio.com")
