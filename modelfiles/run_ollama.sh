#!/bin/bash

ollama serve &

# Guardamos el ID del proceso del servidor para esperarlo luego
PID=$!

echo "⏳ Esperando 60 segundos a que el servidor esté listo..."
sleep 60

# ----------------------------------------------------
# 3. EJECUTAMOS TU SCRIPT DE MODELOS
# ----------------------------------------------------
echo "Lanzando script de creación de modelos..."

# Ejecutamos tu script (asegurándonos de la ruta relativa)
./qwen/QWEN_7B_create_models.sh

echo "Script de modelos finalizado."
# ----------------------------------------------------

# 4. CRÍTICO: Mantener el contenedor vivo
# Si el script termina aquí, Docker se apaga.
# El comando wait espera infinitamente a que termine el proceso de 'ollama serve'
wait $PID