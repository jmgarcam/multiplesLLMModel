#!/bin/bash

echo "Iniciando creación de modelos LLAMA_8b..."

# --- NO_RAG ---
echo "Creando LLAMA_8b NO_RAG (T1, T2, T3)..."
ollama create LLAMA_8b_LLM_resumen_NO_RAG_T1 -f ./LLAMA_8B_LLM_resumir_NO_RAG_T1.txt
ollama create LLAMA_8b_LLM_resumen_NO_RAG_T2 -f ./LLAMA_8B_LLM_resumir_NO_RAG_T2.txt
ollama create LLAMA_8b_LLM_resumen_NO_RAG_T3 -f ./LLAMA_8B_LLM_resumir_NO_RAG_T3.txt

# --- RAG ---
echo "Creando LLAMA_8b RAG (T1, T2, T3)..."
ollama create LLAMA_8b_LLM_resumen_RAG_T1 -f ./llama/LLAMA_8B_LLM_resumir_RAG_T1.txt
ollama create LLAMA_8b_LLM_resumen_RAG_T2 -f ./llama/LLAMA_8B_LLM_resumir_RAG_T2.txt
ollama create LLAMA_8b_LLM_resumen_RAG_T3 -f ./llama/LLAMA_8B_LLM_resumir_RAG_T3.txt

echo "¡Proceso finalizado! Lista de modelos actuales:"
ollama list | grep LLAMA_8b_LLM_resumen