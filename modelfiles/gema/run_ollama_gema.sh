#!/bin/bash

ollama serve &

# Guardamos el ID del proceso del servidor para esperarlo luego
PID=$!

echo "Esperando 60 segundos a que el servidor esté listo..."
sleep 60

echo "Iniciando creación de modelos GEMA_9B..."

# --- NO_RAG ---
echo "Creando GEMA_9B NO_RAG (T1, T2, T3)..."
ollama create GEMA_9B_LLM_resumen_NO_RAG_T1 -f ./gema/GEMA_9B_LLM_resumir_NO_RAG_T1.txt
ollama create GEMA_9B_LLM_resumen_NO_RAG_T2 -f ./gema/GEMA_9B_LLM_resumir_NO_RAG_T2.txt
ollama create GEMA_9B_LLM_resumen_NO_RAG_T3 -f ./gema/GEMA_9B_LLM_resumir_NO_RAG_T3.txt

# --- RAG ---
echo "Creando GEMA_9B RAG (T1, T2, T3)..."
ollama create GEMA_9B_LLM_resumen_RAG_T1 -f ./gema/GEMA_9B_LLM_resumir_RAG_T1.txt
ollama create GEMA_9B_LLM_resumen_RAG_T2 -f ./gema/GEMA_9B_LLM_resumir_RAG_T2.txt
ollama create GEMA_9B_LLM_resumen_RAG_T3 -f ./gema/GEMA_9B_LLM_resumir_RAG_T3.txt

echo "¡Proceso finalizado! Lista de modelos actuales:"
ollama list | grep GEMA_9B_LLM_resumen

echo "Script de modelos finalizado."
# ----------------------------------------------------

#Mantener el contenedor vivo
wait $PID