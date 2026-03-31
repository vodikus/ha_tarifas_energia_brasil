def load_last_data_sync():
    """Versão síncrona para uso em propriedades de entidades."""
    if not os.path.exists(LAST_DATA_FILE):
        return None
    try:
        with open(LAST_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler last_data.json (sync): {e}")
        return None

import os
import json
from datetime import datetime
import asyncio
import aiofiles

# Caminho para o arquivo de persistência dos últimos dados
LAST_DATA_FILE = os.path.join(os.path.dirname(__file__), "last_data.json")

async def save_last_data(tarifa_vigente, bandeira_vigente, api_status):
    """Salva o último valor dos sensores e status da API em last_data.json (assíncrono). Só sobrescreve se houver valor válido. Se ambos forem None, retorna o valor atual do arquivo."""
    if tarifa_vigente is None and bandeira_vigente is None:
        # Retorna o valor atual do arquivo
        if os.path.exists(LAST_DATA_FILE):
            async with aiofiles.open(LAST_DATA_FILE, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        return None
    data = {
        "tarifa_vigente": tarifa_vigente,
        "bandeira_vigente": bandeira_vigente,
        "api_status": api_status,
        "timestamp": datetime.now().isoformat()
    }
    try:
        async with aiofiles.open(LAST_DATA_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data))
        return data
    except Exception as e:
        print(f"Erro ao salvar last_data.json: {e}")
        return None

async def load_last_data():
    """Carrega o último valor dos sensores e status da API de last_data.json (assíncrono)."""
    if not os.path.exists(LAST_DATA_FILE):
        return None
    try:
        async with aiofiles.open(LAST_DATA_FILE, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        print(f"Erro ao ler last_data.json: {e}")
        return None