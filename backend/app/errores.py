"""Errores de la API con el formato del contrato: {"error": "mensaje en español"}.

Uso en cualquier parte del backend:

    from app.errores import ErrorApi
    raise ErrorApi(404, "SPHEREx no tiene imágenes de esa zona.")

main.py convierte ese error en la respuesta HTTP correcta (ver docs/api.md, sección Errores).
"""


class ErrorApi(Exception):
    """Un error que se le muestra al usuario tal cual, con su código HTTP."""

    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
