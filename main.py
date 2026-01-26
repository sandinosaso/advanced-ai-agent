from __future__ import annotations

from fastapi import FastAPI, HTTPException

from db import fetch_all, table_exists


app = FastAPI()


@app.get("/user")
def list_user_content():
    """Conecta a MySQL (según .env) y lista el contenido.

    - Si existe la tabla `user`, devuelve hasta 100 filas.
    - Si no existe, devuelve la lista de tablas.
    """
    try:
        if table_exists("user"):
            rows = fetch_all("SELECT * FROM user LIMIT 100")
            return {"table": "user", "rows": rows}

        tables = fetch_all("SHOW TABLES")
        # mysql-connector devuelve la columna con nombre variable; devolvemos los valores
        table_names = [list(row.values())[0] for row in tables]
        return {"table": None, "tables": table_names}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
