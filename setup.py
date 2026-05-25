# setup.py
import os

structure = {
    # backend FastAPI + RTDB
    "functions": ["__init__.py", "main.py"],
    "functions/domain": ["__init__.py", "types.py"],
    "functions/api_routes": ["__init__.py", "pesquisas.py", "processamento.py"],
    "functions/services": ["__init__.py", "pesquisa.py", "analytics.py"],
    "functions/ingest": ["__init__.py", "openalex.py"],
    "functions/workers": [
        "__init__.py",
        "batch_processor.py",
        "resolvers.py",
        "upsert.py",
        "openalex_mapper.py",
    ],

    # frontend (placeholder para sua apresentação)
    "apresentacao/pages": ["__init__.py", "index.py"],
    "apresentacao/components": ["__init__.py", "header.py", "footer.py"],
    "apresentacao/services": ["__init__.py", "firebase.py"],

    # config e infra local
    "config": ["__init__.py", "settings.py", "firebase_admin_init.py"],

    # raiz do projeto
    ".": [
        "requirements.txt",
        ".env",                # você preenche depois
        "firestore.rules",     # mantido caso use Firestore no futuro
        "firestore.indexes.json",
        "storage.rules",
        "firebase.json",
        ".firebaserc",
        "README.md",
    ],
}

HEADER = "# TODO: implementar\n"

def touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            if path.endswith(".py"):
                f.write(HEADER)

def main():
    print("🔧 Criando estrutura de pastas e arquivos vazios...")
    for folder, files in structure.items():
        os.makedirs(folder, exist_ok=True)
        for fname in files:
            touch(os.path.join(folder, fname))
    print("✅ Pronto! Agora preencha os arquivos conforme sua implementação.")

if __name__ == "__main__":
    main()
