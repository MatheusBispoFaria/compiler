"""Entrada compatível para analisar o arquivo de transcrição pelo terminal."""

import json
from pathlib import Path

from analysis_engine import analisar_transcricao


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    text = (root / "data/transcricao.txt").read_text(encoding="utf-8-sig")
    result = analisar_transcricao(text)
    (root / "Data.json/dados.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Análise concluída. A gravação no histórico é feita pelo aplicativo.")
