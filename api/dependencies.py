from __future__ import annotations

from functools import lru_cache
import os

from application.services import ApplicationServices, create_application_services


@lru_cache(maxsize=1)
def get_services() -> ApplicationServices:
    return create_application_services(os.getenv("GENETIC_CIRCUIT_API_DATA_DIR"))
