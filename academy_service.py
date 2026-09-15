import urllib.request
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AcademyService")

class AcademyService:
    def __init__(self, base_url="https://academy.infectocast.com.br/api", token="idIsYOe8egEasc4xwhxmwu2uSZyWy3oEhWzE3kEHakhcPJzQpp7kGLmYrk7lcrMQ"):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InfectoCast-Dashboard/2.0"
        }

    def _request(self, endpoint, method="GET", timeout=12):
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict):
                    if "data" in data:
                        return data["data"]
                    return data
                return data
        except urllib.error.HTTPError as e:
            # 404 might mean endpoint not yet deployed or course has no sub-items
            logger.warning(f"HTTP {e.code} on {endpoint}: {e.reason}")
            return None
        except Exception as e:
            logger.error(f"Error requesting {endpoint}: {e}")
            return None

    def get_cursos(self):
        """
        GET /cursos
        Retorna a lista oficial de cursos cadastrados no Academy.
        """
        data = self._request("/cursos")
        if data and isinstance(data, list):
            # Filtra cursos de teste ou externos se necessário
            return [c for c in data if "teste" not in str(c.get("nome", "")).lower()]
        return data or []

    def get_turmas(self, id_curso):
        """
        GET /cursos/{id_curso}/turmas
        Retorna todas as turmas cadastradas para um determinado curso.
        """
        data = self._request(f"/cursos/{id_curso}/turmas")
        return data or []

    def get_turma_detalhe(self, id_curso, id_turma):
        """
        GET /cursos/{id_curso}/turmas/{id_turma}
        Retorna o detalhamento completo de uma determinada turma.
        """
        return self._request(f"/cursos/{id_curso}/turmas/{id_turma}")

    def get_modulos(self, id_curso):
        """
        GET /cursos/{id_curso}/modulos
        Retorna a lista de módulos de um determinado curso.
        """
        data = self._request(f"/cursos/{id_curso}/modulos")
        return data or []

    def get_aulas(self, id_curso, id_modulo):
        """
        GET /cursos/{id_curso}/modulos/{id_modulo}/aulas
        Retorna a lista de aulas de um determinado módulo.
        """
        data = self._request(f"/cursos/{id_curso}/modulos/{id_modulo}/aulas")
        return data or []

    def get_curriculo_completo(self, fallback_curriculum=None):
        """
        Constrói o mapa completo do currículo:
        {
          "Nome do Curso": [
             {
               "modulo": "Módulo 1",
               "n_curric": 10,
               "aulas": [
                  {"id": 123, "nome": "Aula 1", "curriculo": True}, ...
               ]
             }, ...
          ]
        }
        Se os endpoints de módulos/aulas retornarem vazio/404, faz fallback elegante.
        """
        cursos = self.get_cursos()
        if not cursos:
            logger.info("Nenhum curso retornado da API. Usando fallback.")
            return fallback_curriculum or {}

        curriculo_dinamico = {}
        api_has_modules = False

        for c in cursos:
            cid = c.get("id")
            cnome = c.get("nome", "").strip()
            if not cnome:
                continue

            modulos = self.get_modulos(cid)
            if modulos:
                api_has_modules = True
                curriculo_dinamico[cnome] = []
                for m in modulos:
                    mid = m.get("id")
                    mnome = m.get("nome") or m.get("titulo") or f"Módulo {mid}"
                    aulas = self.get_aulas(cid, mid) or []
                    
                    aulas_formatadas = []
                    for a in aulas:
                        aulas_formatadas.append({
                            "id": a.get("id"),
                            "nome": a.get("nome") or a.get("titulo") or "",
                            "duracao": a.get("duracao", 0),
                            "ordem": a.get("ordem", 1),
                            "curriculo": True
                        })
                    
                    curriculo_dinamico[cnome].append({
                        "modulo": mnome,
                        "n_curric": len(aulas_formatadas),
                        "aulas": aulas_formatadas
                    })

        if api_has_modules:
            logger.info(f"Currículo 100% dinâmico gerado via API para {len(curriculo_dinamico)} cursos!")
            return curriculo_dinamico
        else:
            logger.info("Endpoints de módulos/aulas ainda não retornaram dados (HTTP 404). Mantendo fallback de currículo.")
            return fallback_curriculum or {}

if __name__ == "__main__":
    service = AcademyService()
    cursos = service.get_cursos()
    print(f"Cursos oficiais retornados da API ({len(cursos)}):")
    for c in cursos:
        print(f"  [{c.get('id')}] {c.get('nome')} (Tipo: {c.get('tipo')})")
