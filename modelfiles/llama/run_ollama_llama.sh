#!/bin/bash

ollama serve &

# Guardamos el ID del proceso del servidor para esperarlo luego
PID=$!

echo "Esperando 60 segundos a que el servidor esté listo..."
sleep 60

# Ejecutar creación de modelos
echo "Iniciando creación de modelos LLAMA_1B..."

# --- NO_RAG ---
echo "Creando LLAMA_1B NO_RAG (T1, T2, T3)..."
ollama create LLAMA_1B_LLM_resumen_NO_RAG_T1 -f ./llama/LLAMA_1B_LLM_resumir_NO_RAG_T1.txt
ollama create LLAMA_1B_LLM_resumen_NO_RAG_T2 -f ./llama/LLAMA_1B_LLM_resumir_NO_RAG_T2.txt
ollama create LLAMA_1B_LLM_resumen_NO_RAG_T3 -f ./llama/LLAMA_1B_LLM_resumir_NO_RAG_T3.txt

# --- RAG ---
echo "Creando LLAMA_1B RAG (T1, T2, T3)..."
ollama create LLAMA_1B_LLM_resumen_RAG_T1 -f ./llama/LLAMA_1B_LLM_resumir_RAG_T1.txt
ollama create LLAMA_1B_LLM_resumen_RAG_T2 -f ./llama/LLAMA_1B_LLM_resumir_RAG_T2.txt
ollama create LLAMA_1B_LLM_resumen_RAG_T3 -f ./llama/LLAMA_1B_LLM_resumir_RAG_T3.txt

echo "¡Proceso finalizado! Lista de modelos actuales:"
ollama list | grep LLAMA_1B_LLM_resumen

echo "Script de modelos finalizado."
# ----------------------------------------------------

#Mantener el contenedor vivo
wait $PID