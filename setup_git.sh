#!/usr/bin/env bash

# ------------------------------------------------------------
# Proyecto: Fina‑Seinen
# Script de inicialización y envío a GitHub
# ------------------------------------------------------------

# 1️⃣ Inicializar repositorio Git (solo la primera vez)
if [ ! -d ".git" ]; then
  git init
  echo "Repositorio Git inicializado."
else
  echo "Repositorio Git ya existe."
fi

# 2️⃣ Añadir todos los archivos y crear el primer commit
git add .
# Si ya hay un commit previo, este comando no hará nada
if git commit -m "Inicial: proyecto Fina‑Seinen (modernizado)"; then
  echo "Commit creado."
else
  echo "No hay cambios para commitear."
fi

# 3️⃣ Configurar remote (reemplaza <URL-REPO> por tu URL HTTPS o SSH)
# Ejemplo HTTPS: https://github.com/dankopetro/Fina-Seinen.git
# Ejemplo SSH:   git@github.com:dankopetro/Fina-Seinen.git
REMOTE_URL="$1"
if [ -z "$REMOTE_URL" ]; then
  echo "Error: Debes pasar la URL del remote como argumento."
  exit 1
fi
if [ -n "$REMOTE_URL" ]; then
  git remote add origin "$REMOTE_URL" || git remote set-url origin "$REMOTE_URL"
  echo "Remote configurado como $REMOTE_URL"
else
  echo "Remote no configurado – debes ejecutarlo manualmente después."
fi

# 4️⃣ Push al branch principal (main)
if git branch | grep -q "main"; then
  BRANCH="main"
else
  git branch -M main
  BRANCH="main"
fi

git push -u origin "$BRANCH"

echo "---"
echo "Proceso completado. Si el push falla, revisa la URL del remote y tus credenciales de GitHub."
