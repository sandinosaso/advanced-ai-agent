FastAPI + MySQL

Requisitos
- Python 3.10+

Setup
- Crear `.env` en la raíz (puedes copiar `.env.example`).
- Instalar dependencias: `pip install -r requirements.txt`

Ejecutar
- `uvicorn main:app --reload --port 8000`

Endpoint
- `GET /user`: si existe la tabla `user`, devuelve hasta 100 filas; si no, lista las tablas.