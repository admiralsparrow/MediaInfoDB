#!/bin/sh
set -e

echo "Running database migrations..."
# Stamp pre-release databases (revisions 002-013) to the squashed 001 migration.
# Done via SQL because the old revision files no longer exist for alembic to resolve.
python3 -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def stamp():
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text('SELECT version_num FROM alembic_version'))
            row = result.fetchone()
            if row and row[0] != '001':
                await conn.execute(text(\"UPDATE alembic_version SET version_num = '001'\"))
                print(f'Stamped alembic_version from {row[0]} to 001')
        except Exception:
            pass
    await engine.dispose()

asyncio.run(stamp())
" || true
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2}
