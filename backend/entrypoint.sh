#!/usr/bin/env sh
set -e

until python -c "import os; from sqlalchemy import create_engine; create_engine(os.getenv('DATABASE_URL')).connect().close()" 2>/dev/null; do
  echo "Aguardando banco de dados..."
  sleep 2
done

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
