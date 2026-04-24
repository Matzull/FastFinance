"""Minimal FastAPI client for the Kivy mobile app."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class ApiClientError(RuntimeError):
    """Raised when a backend request fails."""


@dataclass
class FastFinanceApiClient:
    """HTTP client for FastFinance backend endpoints."""

    base_url: str
    timeout_seconds: int = 10

    def set_base_url(self, base_url: str) -> None:
        self.base_url = base_url.strip().rstrip("/")

    def get_summary(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/resumen")

    def list_transactions(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._request_json("GET", f"/api/transacciones?limite={limit}")

    def create_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/transacciones", payload)

    def delete_transaction(self, transaction_id: int) -> dict[str, Any]:
        return self._request_json("DELETE", f"/api/transacciones/{transaction_id}")

    def list_banks(self, active_only: bool = True) -> list[dict[str, Any]]:
        flag = "true" if active_only else "false"
        return self._request_json("GET", f"/api/bancos?solo_activos={flag}")

    def create_bank(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/bancos", payload)

    def delete_bank(self, bank_id: int) -> dict[str, Any]:
        return self._request_json("DELETE", f"/api/bancos/{bank_id}")

    def list_subscriptions(self, active_only: bool = True) -> list[dict[str, Any]]:
        flag = "true" if active_only else "false"
        return self._request_json("GET", f"/api/suscripciones?solo_activas={flag}")

    def create_subscription(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/suscripciones", payload)

    def cancel_subscription(self, subscription_id: int) -> dict[str, Any]:
        return self._request_json("DELETE", f"/api/suscripciones/{subscription_id}")

    def list_net_worth_items(self, item_type: str | None = None) -> list[dict[str, Any]]:
        if item_type:
            return self._request_json("GET", f"/api/patrimonio?tipo={item_type}")
        return self._request_json("GET", "/api/patrimonio")

    def create_net_worth_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/patrimonio", payload)

    def delete_net_worth_item(self, item_id: int) -> dict[str, Any]:
        return self._request_json("DELETE", f"/api/patrimonio/{item_id}")

    def list_budgets(self, active_only: bool = True) -> list[dict[str, Any]]:
        flag = "true" if active_only else "false"
        return self._request_json("GET", f"/api/presupuestos?solo_activos={flag}")

    def get_budget_status(self) -> list[dict[str, Any]]:
        return self._request_json("GET", "/api/presupuestos/estado")

    def create_budget(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/presupuestos", payload)

    def update_budget(self, budget_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("PUT", f"/api/presupuestos/{budget_id}", payload)

    def delete_budget(self, budget_id: int) -> dict[str, Any]:
        return self._request_json("DELETE", f"/api/presupuestos/{budget_id}")

    def get_insights(self) -> dict[str, Any]:
        return self._request_json("GET", "/api/insights")

    def expenses_by_category(self) -> list[dict[str, Any]]:
        return self._request_json("GET", "/api/estadisticas/gastos-por-categoria")

    def monthly_evolution(self, months: int = 12) -> list[dict[str, Any]]:
        return self._request_json("GET", f"/api/estadisticas/evolucion-mensual?meses={months}")

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        base = self.base_url.strip().rstrip("/")
        if not base:
            raise ApiClientError("Base URL is empty")

        body: bytes | None = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(
            url=f"{base}{path}",
            method=method,
            headers=headers,
            data=body,
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            try:
                data = json.loads(exc.read().decode("utf-8"))
                detail = data.get("detail") or data
            except Exception:
                detail = exc.reason
            raise ApiClientError(f"HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise ApiClientError(f"Could not connect to backend: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ApiClientError("Backend request timed out") from exc
