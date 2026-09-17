# -*- coding: utf-8 -*-
"""
Serviço Oficial de Integração com a API InfectoCast Academy
- Extração ao vivo de Cursos, Módulos e Aulas
- Mapeamento e consolidação curricular automática
"""

import os
import urllib.request
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AcademyService")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "academy_curriculum_cache.json")

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
            logger.warning(f"HTTP {e.code} on {endpoint}: {e.reason}")
            return None
        except Exception as e:
            logger.error(f"Error requesting {endpoint}: {e}")
            return None

    def get_cursos(self):
        """GET /cursos"""
        data = self._request("/cursos")
        if data and isinstance(data, list):
            return [c for c in data if "teste" not in str(c.get("nome", "")).lower()]
        return data or []

    def get_modulos(self, id_curso):
        """GET /cursos/{id_curso}/modulos"""
        data = self._request(f"/cursos/{id_curso}/modulos")
        return data or []

    def get_aulas(self, id_curso, id_modulo):
        """GET /cursos/{id_curso}/modulos/{id_modulo}/aulas"""
        data = self._request(f"/cursos/{id_curso}/modulos/{id_modulo}/aulas")
        return data or []

    def get_curriculo_completo(self, force_refresh=False):
        """
        Retorna o mapa curricular estruturado de cursos, módulos e aulas:
        {
          "Nome do Curso": [
             {
               "id_modulo": 1073,
               "modulo": "Epidemiologia...",
               "n_curric": 21,
               "aulas": [
                  {"id": 100363, "nome": "Introdução...", "ordem": 1, "curriculo": True}, ...
               ]
             }
          ]
        }
        """
        if not force_refresh and os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if cached and len(cached) > 0:
                        logger.info(f"Carregados {len(cached)} cursos do cache curricular da Academy.")
                        return cached
            except Exception as e:
                logger.warning(f"Erro ao ler cache curricular: {e}")

        cursos = self.get_cursos()
        if not cursos:
            logger.warning("Nenhum curso retornado da API Academy.")
            return {}

        curriculo_dinamico = {}
        for c in cursos:
            cid = c.get("id")
            cnome = str(c.get("nome", "")).strip()
            if not cnome:
                continue

            modulos = self.get_modulos(cid) or []
            if not modulos:
                continue

            curriculo_dinamico[cnome] = []
            for m in modulos:
                mid = m.get("id")
                mnome = str(m.get("nome") or f"Módulo {mid}").strip()
                ordem_m = m.get("ordem", 1)
                
                aulas = self.get_aulas(cid, mid) or []
                aulas_formatadas = []
                for a in aulas:
                    aulas_formatadas.append({
                        "id": a.get("id"),
                        "nome": str(a.get("nome") or "").strip(),
                        "ordem": a.get("ordem", 1),
                        "duracao": a.get("duracao", 0),
                        "curriculo": True
                    })

                curriculo_dinamico[cnome].append({
                    "id_modulo": mid,
                    "modulo": mnome,
                    "ordem": ordem_m,
                    "n_curric": len(aulas_formatadas),
                    "aulas": aulas_formatadas
                })
            time.sleep(0.05)

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(curriculo_dinamico, f, indent=2, ensure_ascii=False)

        logger.info(f"Currículo 100% dinâmico da Academy extraído: {len(curriculo_dinamico)} cursos salvos em cache!")
        return curriculo_dinamico

if __name__ == "__main__":
    service = AcademyService()
    curriculo = service.get_curriculo_completo(force_refresh=True)
    print(f"Currículo completo carregado: {len(curriculo)} cursos.")
