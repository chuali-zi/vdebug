from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from lot.contracts.errors import DomainError
from lot.contracts.models import IoResult, SimEvent, StepResult
from lot.devices.registry import DeviceRegistry, DeviceRuntime
from lot.engine.clock import VirtualClock
from lot.engine.scheduler import SchedulerQueue, ScheduledEvent
from lot.session.models import RuntimeContext


@dataclass(slots=True)
class EngineServiceStub:
    """Execution core skeleton for Mode A."""

    device_registry: DeviceRegistry

    def step(self, runtime: RuntimeContext, delta_ms: int) -> StepResult:
        clock = VirtualClock(now_ns=runtime.now_ns)
        start_ns = clock.now_ns
        target_ns = clock.preview_advance_ms(delta_ms)
        scheduler = SchedulerQueue.from_runtime_state(runtime.scheduler_items)
        due_items = scheduler.drain_due(target_ns)

        events: list[SimEvent] = []
        for item in due_items:
            clock.advance_to(item.due_ns)
            events.extend(self._dispatch_scheduled_event(runtime, item))

        clock.advance_to(target_ns)
        runtime.now_ns = clock.now_ns
        runtime.scheduler_items = scheduler.to_runtime_state()

        return StepResult(
            now_ns=runtime.now_ns,
            events=events,
            state_delta={
                "engine": {
                    "advanced_from_ns": start_ns,
                    "advanced_to_ns": runtime.now_ns,
                    "processed_events": len(events),
                    "pending_events": scheduler.count(),
                },
                "device_state": deepcopy(runtime.device_state),
            },
        )

    def execute_io(self, runtime: RuntimeContext, bus_action: str, payload: dict[str, object]) -> IoResult:
        result, events = self._apply_io_action(
            runtime,
            bus_action=bus_action,
            payload=payload,
            source="engine.io",
        )
        return IoResult(
            result=result,
            events=events,
            state_delta={
                "engine": {
                    "now_ns": runtime.now_ns,
                    "pending_events": len(runtime.scheduler_items),
                },
                "device_state": deepcopy(runtime.device_state),
            },
        )

    def snapshot(self, runtime: RuntimeContext) -> dict[str, object]:
        scheduler = SchedulerQueue.from_runtime_state(runtime.scheduler_items)
        return {
            "now_ns": runtime.now_ns,
            "pending_events": scheduler.count(),
            "scheduler": scheduler.to_public_state(),
            "device_state": deepcopy(runtime.device_state),
        }

    def enqueue(
        self,
        runtime: RuntimeContext,
        due_ns: int,
        kind: str,
        payload: dict[str, object],
        priority: int = 100,
    ) -> None:
        scheduler = SchedulerQueue.from_runtime_state(runtime.scheduler_items)
        scheduler.enqueue(
            due_ns=due_ns,
            kind=kind,
            payload=payload,
            priority=priority,
        )
        runtime.scheduler_items = scheduler.to_runtime_state()

    def _dispatch_scheduled_event(self, runtime: RuntimeContext, item: ScheduledEvent) -> list[SimEvent]:
        if item.kind in {"io", "bus_io"}:
            bus_action = item.payload.get("bus_action")
            params = item.payload.get("params", {})
            if not isinstance(bus_action, str):
                raise DomainError(
                    error_code="INVALID_SCHEDULED_IO_EVENT",
                    message="Scheduled I/O item is missing bus_action.",
                    explain="A scheduled I/O event must declare the public bus_action string.",
                    next_actions=["Enqueue the event with payload.bus_action set to '<bus>:<action>'."],
                )
            if not isinstance(params, dict):
                raise DomainError(
                    error_code="INVALID_SCHEDULED_IO_EVENT",
                    message="Scheduled I/O params must be a dictionary.",
                    explain="Engine only dispatches scheduled I/O commands with JSON-like params.",
                    next_actions=["Enqueue the event with payload.params as an object."],
                )
            _, events = self._apply_io_action(
                runtime,
                bus_action=bus_action,
                payload=params,
                t_virtual_ns=item.due_ns,
                source="engine.scheduler",
                scheduled_kind=item.kind,
            )
            return events

        return [
            self._new_event(
                runtime=runtime,
                t_virtual_ns=item.due_ns,
                source="engine.scheduler",
                event_type="SCHEDULED_EVENT_DISPATCHED",
                payload={
                    "kind": item.kind,
                    "priority": item.priority,
                    "payload": deepcopy(item.payload),
                },
            )
        ]

    def _apply_io_action(
        self,
        runtime: RuntimeContext,
        *,
        bus_action: str,
        payload: dict[str, object],
        source: str,
        t_virtual_ns: int | None = None,
        scheduled_kind: str | None = None,
    ) -> tuple[dict[str, object], list[SimEvent]]:
        if not isinstance(payload, dict):
            raise DomainError(
                error_code="INVALID_IO_PAYLOAD",
                message="I/O payload must be a dictionary.",
                explain="Bus commands cross module boundaries as JSON-like objects.",
                next_actions=["Retry with a JSON object payload."],
            )

        device_runtime = self._device_runtime(runtime)
        effective_now_ns = runtime.now_ns if t_virtual_ns is None else t_virtual_ns
        if bus_action == "fault:inject":
            outcome = device_runtime.inject_fault(
                str(payload.get("fault_kind", "")),
                dict(payload),
                effective_now_ns,
            )
            event = self._new_event(
                runtime=runtime,
                t_virtual_ns=effective_now_ns,
                source=source,
                event_type="FAULT_INJECT",
                payload={
                    "bus": "fault",
                    "action": "inject",
                    "params": deepcopy(payload),
                    "result": deepcopy(outcome["result"]),
                    "scheduled": scheduled_kind is not None,
                    "scheduled_kind": scheduled_kind,
                },
            )
            return outcome["result"], [event]

        bus, action = self._parse_bus_action(bus_action)
        outcome = device_runtime.execute(bus_action, dict(payload), effective_now_ns)
        self._update_public_bus_state(runtime, bus, action, payload)
        event_type = f"{bus.upper()}_{action.upper()}"
        if scheduled_kind is not None:
            event_type = f"SCHEDULED_{event_type}"

        event = self._new_event(
            runtime=runtime,
            t_virtual_ns=effective_now_ns,
            source=source,
            event_type=event_type,
            payload={
                "bus": bus,
                "action": action,
                "params": deepcopy(payload),
                "result": deepcopy(outcome["result"]),
                "scheduled": scheduled_kind is not None,
                "scheduled_kind": scheduled_kind,
            },
        )
        return outcome["result"], [event]

    def _device_runtime(self, runtime: RuntimeContext) -> DeviceRuntime:
        device_runtime = DeviceRuntime(
            registry=self.device_registry,
            session_id=runtime.session_id,
            storage=runtime.device_registry,
        )
        if not runtime.device_registry.get("devices"):
            device_runtime.register_from_board(runtime.board_profile)
        return device_runtime

    def _update_public_bus_state(
        self,
        runtime: RuntimeContext,
        bus: str,
        action: str,
        payload: dict[str, object],
    ) -> None:
        current_bus_state = runtime.device_state.get(bus, {})
        bus_state = deepcopy(current_bus_state) if isinstance(current_bus_state, dict) else {}

        if bus == "gpio":
            self._apply_gpio_action(bus_state, action, payload)
        elif bus == "uart":
            self._apply_uart_action(bus_state, action, payload)
        elif bus == "i2c":
            self._apply_i2c_action(bus_state, action, payload)

        runtime.device_state[bus] = bus_state

    def _apply_gpio_action(
        self,
        bus_state: dict[str, object],
        action: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        pins = bus_state.setdefault("pins", {})
        if not isinstance(pins, dict):
            pins = {}
            bus_state["pins"] = pins

        pin = payload.get("pin")
        if action in {"set", "write"}:
            value = payload.get("value", payload.get("level", 1))
            if isinstance(pin, str):
                pins[pin] = value
            bus_state["last_pin"] = pin
            bus_state["last_value"] = value
            return {"accepted": True, "bus": "gpio", "action": action, "pin": pin, "value": value}

        if action == "toggle":
            current = pins.get(pin, 0)
            next_value = 0 if bool(current) else 1
            if isinstance(pin, str):
                pins[pin] = next_value
            bus_state["last_pin"] = pin
            bus_state["last_value"] = next_value
            return {"accepted": True, "bus": "gpio", "action": action, "pin": pin, "value": next_value}

        if action in {"read", "get"}:
            value = pins.get(pin)
            bus_state["last_pin"] = pin
            bus_state["last_value"] = value
            return {"accepted": True, "bus": "gpio", "action": action, "pin": pin, "value": value}

        bus_state["last_action"] = action
        return {"accepted": True, "bus": "gpio", "action": action, "params": deepcopy(payload)}

    def _apply_uart_action(
        self,
        bus_state: dict[str, object],
        action: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        tx_log = bus_state.setdefault("tx_log", [])
        rx_log = bus_state.setdefault("rx_log", [])
        if not isinstance(tx_log, list):
            tx_log = []
            bus_state["tx_log"] = tx_log
        if not isinstance(rx_log, list):
            rx_log = []
            bus_state["rx_log"] = rx_log

        channel = payload.get("port", "uart0")
        data = payload.get("data", payload.get("bytes", ""))

        if action in {"send", "write"}:
            tx_log.append({"channel": channel, "data": data})
            bus_state["last_tx"] = {"channel": channel, "data": data}
            return {"accepted": True, "bus": "uart", "action": action, "channel": channel, "data": data}

        if action in {"receive", "read"}:
            rx_log.append({"channel": channel, "data": data})
            bus_state["last_rx"] = {"channel": channel, "data": data}
            return {"accepted": True, "bus": "uart", "action": action, "channel": channel, "data": data}

        bus_state["last_action"] = action
        return {"accepted": True, "bus": "uart", "action": action, "params": deepcopy(payload)}

    def _apply_i2c_action(
        self,
        bus_state: dict[str, object],
        action: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        transactions = bus_state.setdefault("transactions", [])
        if not isinstance(transactions, list):
            transactions = []
            bus_state["transactions"] = transactions

        transaction = {
            "action": action,
            "addr_7bit": payload.get("addr_7bit", payload.get("address")),
            "register": payload.get("register"),
            "data": deepcopy(payload.get("data")),
        }
        transactions.append(transaction)
        bus_state["last_transaction"] = transaction
        return {"accepted": True, "bus": "i2c", **transaction}

    def _parse_bus_action(self, bus_action: str) -> tuple[str, str]:
        if not isinstance(bus_action, str) or ":" not in bus_action:
            raise DomainError(
                error_code="INVALID_BUS_ACTION",
                message=f"Invalid bus_action: {bus_action!r}",
                explain="Engine bus actions must use the '<bus>:<action>' format.",
                next_actions=["Retry with a bus action like 'gpio:set' or 'uart:send'."],
            )

        bus, action = bus_action.split(":", 1)
        if not bus or not action:
            raise DomainError(
                error_code="INVALID_BUS_ACTION",
                message=f"Invalid bus_action: {bus_action!r}",
                explain="Both the bus segment and action segment are required.",
                next_actions=["Retry with a bus action like 'i2c:write'."],
            )

        supported_buses = set(self.device_registry.supported_buses())
        if bus not in supported_buses:
            raise DomainError(
                error_code="BUS_NOT_SUPPORTED",
                message=f"Unsupported bus: {bus}",
                explain="Requested bus is not registered in the device registry.",
                details={"supported_buses": sorted(supported_buses)},
                next_actions=["Retry with a supported bus name."],
            )

        return bus, action

    def _new_event(
        self,
        *,
        runtime: RuntimeContext,
        t_virtual_ns: int,
        source: str,
        event_type: str,
        payload: dict[str, object],
    ) -> SimEvent:
        return SimEvent(
            session_id=runtime.session_id,
            t_virtual_ns=t_virtual_ns,
            source=source,
            type=event_type,
            severity="info",
            payload=payload,
        )
