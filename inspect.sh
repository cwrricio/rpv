#!/bin/bash
# Script para inspecionar dados no RTDB e API local

echo "===== PRODUTOS (via FastAPI) ====="
curl -s http://127.0.0.1:8000/produtos | jq '.[0:5]'

echo
echo "===== VEICULOS (direto no RTDB) ====="
curl -s "$RTDB_URL/veiculos.json" | jq 'to_entries | .[0:5]'

echo
echo "===== AUTORES (direto no RTDB) ====="
curl -s "$RTDB_URL/autores.json" | jq 'to_entries | .[0:5]'
