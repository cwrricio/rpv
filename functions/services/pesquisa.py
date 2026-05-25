from typing import Optional, List, Dict
from firebase_admin import db
from functions.domain.types import StatusPesquisa, TipoDocente

class PesquisaService:
    def __init__(self):
        self.pesquisas = db.reference("pesquisas")
        self.docentes = db.reference("docentes")

    def _get(self, ref, key: str) -> Dict | None:
        snap = ref.child(key).get()
        return snap if isinstance(snap, dict) else None

    def _ensure_orientador_permanente(self, orientador_id: str):
        d = self._get(self.docentes, orientador_id)
        if not d:
            raise ValueError("Orientador inexistente.")
        if d.get("tipo") != TipoDocente.PERMANENTE.value:
            raise ValueError("Orientador deve ser Docente PERMANENTE.")

    def criar(self, data: Dict) -> Dict:
        required = ["titulo","projeto_id","linha_id","orientador_id","discente_id"]
        if any(not data.get(k) for k in required):
            raise ValueError("Projeto, Linha, Orientador e Discente são obrigatórios.")
        self._ensure_orientador_permanente(data["orientador_id"])

        payload = {
            "titulo": data["titulo"],
            "projeto_id": data["projeto_id"],
            "linha_id": data["linha_id"],
            "orientador_id": data["orientador_id"],
            "discente_id": data["discente_id"],
            "status": StatusPesquisa.EM_ANDAMENTO.value,
            "coorientadores": {},
            "data_inicio": str(data.get("data_inicio")) if data.get("data_inicio") else None,
            "data_fim": str(data.get("data_fim")) if data.get("data_fim") else None
        }
        new_ref = self.pesquisas.push(payload)
        return self._to_out(new_ref.key, payload)

    def atualizar_status(self, id_: str, status: StatusPesquisa) -> Dict:
        cur = self._get(self.pesquisas, id_)
        if not cur:
            raise ValueError("Pesquisa não encontrada.")
        self.pesquisas.child(id_).update({"status": status.value})
        cur["status"] = status.value
        return self._to_out(id_, cur)

    def listar(self, status: Optional[StatusPesquisa]=None) -> List[Dict]:
        if status:
            snaps = self.pesquisas.order_by_child("status").equal_to(status.value).get() or {}
        else:
            snaps = self.pesquisas.get() or {}
        out = []
        for k, v in snaps.items():
            if isinstance(v, dict):
                out.append(self._to_out(k, v))
        out.sort(key=lambda x: x["titulo"].lower())
        return out

    def _to_out(self, id_: str, d: Dict) -> Dict:
        return {
            "id": id_,
            "titulo": d.get("titulo"),
            "projeto_id": d.get("projeto_id"),
            "linha_id": d.get("linha_id"),
            "orientador_id": d.get("orientador_id"),
            "discente_id": d.get("discente_id"),
            "data_inicio": d.get("data_inicio"),
            "data_fim": d.get("data_fim"),
            "status": StatusPesquisa(d.get("status", StatusPesquisa.EM_ANDAMENTO.value))
        }
