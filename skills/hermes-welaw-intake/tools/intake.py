"""Offline intake helpers for We Law."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IntakeResult:
    client: dict[str, Any]
    matter: dict[str, Any]
    client_status: str
    matter_status: str

    def render(self) -> str:
        return "\n".join(
            [
                "INTAKE RESULT",
                f"Cliente: {self.client['id']} / {self.client['nombre']}",
                f"Matter: {self.matter['id']}",
                f"Cliente nuevo o reusado: {self.client_status}",
                f"Matter nuevo o reusado: {self.matter_status}",
                f"Carpeta cliente: {self.client.get('drive_path', 'pendiente')}",
                f"Carpeta matter: {self.matter.get('drive_path', 'pendiente')}",
                "Sheets actualizadas: no",
                f"Engagement: {self.matter.get('engagement', 'pendiente')}",
            ]
        )


class Intake:
    def __init__(self, clients: list[dict[str, Any]], matters: list[dict[str, Any]]):
        self.clients = clients
        self.matters = matters

    def open_or_reuse(
        self,
        nombre: str,
        descripcion: str,
        tipo: str = "contractual",
        rfc: str | None = None,
        engagement: str = "pendiente",
    ) -> IntakeResult:
        if not nombre.strip():
            raise ValueError("cliente identificable is required")
        if not descripcion.strip():
            raise ValueError("descripcion del asunto is required")

        client = self._find_client(nombre, rfc)
        client_status = "reusado"
        if client is None:
            client = {
                "id": next_id("CLI", [item["id"] for item in self.clients]),
                "nombre": nombre,
                "rfc": rfc or "",
                "estado": "activo",
            }
            client["drive_path"] = f"Clientes/{client['id']} - {client['nombre']}"
            client_status = "nuevo"

        matter = self._find_matter(client["id"], descripcion)
        matter_status = "reusado"
        if matter is None:
            matter = {
                "id": next_id("MAT", [item["id"] for item in self.matters]),
                "client_id": client["id"],
                "cliente": client["nombre"],
                "tipo": tipo,
                "estado": "prospecto",
                "descripcion": descripcion,
                "fase": "intake",
                "honorarios": 85000,
                "engagement": engagement,
                "drive_path": f"{client['drive_path']}/01-Matters",
            }
            matter["drive_path"] = f"{matter['drive_path']}/{matter['id']} - {short_title(descripcion)}"
            matter_status = "nuevo"

        return IntakeResult(client, matter, client_status, matter_status)

    def _find_client(self, nombre: str, rfc: str | None) -> dict[str, Any] | None:
        wanted = normalize(nombre)
        for client in self.clients:
            if normalize(client.get("nombre", "")) == wanted:
                return client
            if rfc and normalize(client.get("rfc", "")) == normalize(rfc):
                return client
        return None

    def _find_matter(self, client_id: str, descripcion: str) -> dict[str, Any] | None:
        wanted = normalize(descripcion)
        for matter in self.matters:
            if matter.get("client_id") == client_id and normalize(matter.get("descripcion", "")) == wanted:
                return matter
        return None


def next_id(prefix: str, ids: list[str]) -> str:
    max_num = 0
    for item in ids:
        if item.startswith(prefix + "-"):
            try:
                max_num = max(max_num, int(item.split("-", 1)[1]))
            except ValueError:
                continue
    return f"{prefix}-{max_num + 1:03d}"


def normalize(value: str) -> str:
    return " ".join(value.lower().strip().split())


def short_title(value: str) -> str:
    words = [word.capitalize() for word in value.split()[:4]]
    return " ".join(words) or "Asunto"
