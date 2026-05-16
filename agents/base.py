from __future__ import annotations
from schemas.state import DesignState

class AgentProtocol:
    def run(self, state: DesignState) -> DesignState:
        raise NotImplementedError
