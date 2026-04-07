from __future__ import annotations

from dataclasses import dataclass

from lot.contracts.models import IoResult, SimEvent, StepResult
from lot.devices.registry import DeviceRegistry
from lot.engine.clock import VirtualClock
from lot.session.models import RuntimeContext


@dataclass(slots=True)
class EngineServiceStub:
    """Execution core skeleton for Mode A."""

    device_registry: DeviceRegistry

    def step(self, runtime: RuntimeContext, delta_ms: int) -> StepResult:
        clock = VirtualClock(now_ns=runtime.now_ns)
        now_ns = clock.advance_ms(delta_ms)
        runtime.now_ns = now_ns
        runtime.scheduler_items = runtime.scheduler_items

        # TODO(engine): drain due scheduler items in priority order.
        # TODO(engine): dispatch callbacks into devices and collect derived SimEvent objects.
        # TODO(engine): separate platform faults from simulated target behavior.
        return StepResult(now_ns=now_ns, events=[], state_delta={})

    def execute_io(self, runtime: RuntimeContext, bus_action: str, payload: dict[str, object]) -> IoResult:
        # TODO(engine): translate bus_action into a typed bus command and delegate to devices.
        # TODO(engine): create stable SimEvent output for every externally visible operation.
        event = SimEvent(
            session_id=runtime.session_id,
            t_virtual_ns=runtime.now_ns,
            source=f"engine.{bus_action}",
            type="IO_COMMAND_ACCEPTED",
            severity="info",
            payload={"params": payload, "status": "todo"},
        )
        return IoResult(
            result={
                "accepted": True,
                "bus_action": bus_action,
                "note": "Scaffold placeholder only. Real bus semantics are still TODO.",
            },
            events=[event],
            state_delta={},
        )
