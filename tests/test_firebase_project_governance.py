import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_FIREBASE_PROJECT_ID = "poshbard"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_firebaserc_usa_project_id_canonico():
    data = json.loads(_read(".firebaserc"))

    assert data["projects"]["default"] == CANONICAL_FIREBASE_PROJECT_ID


def test_workflows_legados_nao_apontam_para_project_id_antigo():
    workflow_paths = [
        ".github/workflows/firebase-hosting-merge.yml",
        ".github/workflows/firebase-hosting-pull-request.yml",
    ]

    for path in workflow_paths:
        content = _read(path)
        assert "metaorganizer-project" not in content
        assert "FIREBASE_SERVICE_ACCOUNT_METAORGANIZER_PROJECT" not in content
        assert f"FIREBASE_PROJECT_ID: {CANONICAL_FIREBASE_PROJECT_ID}" in content
        assert "FIREBASE_SERVICE_ACCOUNT_POSHBARD" in content


def test_exemplos_firebase_legados_usam_project_id_canonico():
    env_example = _read(".env.example")
    seed_script = _read("scripts/seed_rtdb.py")

    assert f"# PROJECT_ID={CANONICAL_FIREBASE_PROJECT_ID}" in env_example
    assert f"# FIREBASE_PROJECT_ID={CANONICAL_FIREBASE_PROJECT_ID}" in env_example
    assert f"https://{CANONICAL_FIREBASE_PROJECT_ID}-default-rtdb.firebaseio.com" in env_example
    assert f'os.environ.get("FIREBASE_PROJECT_ID") or "{CANONICAL_FIREBASE_PROJECT_ID}"' in seed_script
