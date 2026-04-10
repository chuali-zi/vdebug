from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lot.contracts.errors import DomainError
from lot.contracts.models import BoardProfile
from lot.devices.registry import build_default_device_registry
from lot.engine.service import EngineServiceStub
from lot.session.models import RuntimeContext


class EngineServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EngineServiceStub(device_registry=build_default_device_registry())
        self.runtime = RuntimeContext.from_board_profile(
            session_id="sess-test-engine",
            board_profile=BoardProfile(
                source_path="profiles/example_stm32f4.yaml",
                version="v1alpha1",
                board="example_stm32f4",
                buses={
                    "i2c0": {
                        "kind": "i2c",
                        "pins": {"sda": "PB7", "scl": "PB6"},
                        "pullup_ohm": 4700,
                        "devices": [{"addr_7bit": 0x48, "type": "TMP102"}],
                    },
                    "uart0": {
                        "kind": "uart",
                        "pins": {"tx": "PA2", "rx": "PA3"},
                        "baud": 115200,
                    },
                },
                gpio={
                    "PA0": {"direction": "output", "pull": "none"},
                    "PA1": {"direction": "input", "pull": "up"},
                },
                raw={"board": "example_stm32f4"},
            ),
        )

    def test_step_drains_due_items_by_due_time_priority_and_sequence(self) -> None:
        self.engine.enqueue(
            self.runtime,
            due_ns=1_000_000,
            kind="marker",
            payload={"name": "first-seq"},
            priority=100,
        )
        self.engine.enqueue(
            self.runtime,
            due_ns=1_000_000,
            kind="marker",
            payload={"name": "second-seq"},
            priority=100,
        )
        self.engine.enqueue(
            self.runtime,
            due_ns=1_000_000,
            kind="marker",
            payload={"name": "higher-priority"},
            priority=50,
        )
        self.engine.enqueue(
            self.runtime,
            due_ns=5_000_000,
            kind="marker",
            payload={"name": "future"},
            priority=10,
        )

        result = self.engine.step(self.runtime, 2)

        self.assertEqual(result.now_ns, 2_000_000)
        self.assertEqual(
            [event.payload["payload"]["name"] for event in result.events],
            ["higher-priority", "first-seq", "second-seq"],
        )
        self.assertEqual(len(self.runtime.scheduler_items), 1)
        self.assertEqual(self.runtime.scheduler_items[0]["payload"]["name"], "future")

    def test_execute_io_updates_gpio_state_and_returns_normalized_event(self) -> None:
        result = self.engine.execute_io(
            self.runtime,
            "gpio:set",
            {"pin": "PA0", "value": 1},
        )

        self.assertTrue(result.result["accepted"])
        self.assertEqual(self.runtime.device_state["gpio"]["pins"]["PA0"], 1)
        self.assertEqual(result.events[0].type, "GPIO_SET")
        self.assertEqual(result.events[0].payload["bus"], "gpio")
        self.assertEqual(result.events[0].payload["action"], "set")

    def test_step_dispatches_scheduled_io_through_same_event_model(self) -> None:
        self.engine.enqueue(
            self.runtime,
            due_ns=1_000_000,
            kind="io",
            payload={
                "bus_action": "gpio:set",
                "params": {"pin": "PB3", "value": 0},
            },
            priority=100,
        )

        result = self.engine.step(self.runtime, 1)

        self.assertEqual(self.runtime.device_state["gpio"]["pins"]["PB3"], 0)
        self.assertEqual(result.events[0].type, "SCHEDULED_GPIO_SET")
        self.assertTrue(result.events[0].payload["scheduled"])

    def test_snapshot_reports_runtime_state_without_mutating_it(self) -> None:
        self.engine.enqueue(
            self.runtime,
            due_ns=10_000_000,
            kind="marker",
            payload={"name": "future"},
        )
        self.engine.execute_io(self.runtime, "uart:send", {"port": "uart1", "data": "ping"})

        snapshot = self.engine.snapshot(self.runtime)

        self.assertEqual(snapshot["now_ns"], 0)
        self.assertEqual(snapshot["pending_events"], 1)
        self.assertEqual(snapshot["scheduler"][0]["kind"], "marker")
        self.assertEqual(snapshot["device_state"]["uart"]["last_tx"]["data"], "ping")

    def test_execute_io_rejects_invalid_bus_actions(self) -> None:
        with self.assertRaises(DomainError) as ctx:
            self.engine.execute_io(self.runtime, "invalid", {})

        self.assertEqual(ctx.exception.error_code, "INVALID_BUS_ACTION")

    def test_execute_io_invalid_gpio_payload_does_not_mutate_runtime_state(self) -> None:
        self.engine._device_runtime(self.runtime)
        original_pin_state = dict(self.runtime.device_state["PA0"])

        with self.assertRaises(DomainError) as ctx:
            self.engine.execute_io(self.runtime, "gpio:set", {"pin": "PA0", "value": "bad"})

        self.assertEqual(ctx.exception.error_code, "INVALID_GPIO_VALUE")
        self.assertNotIn("gpio", self.runtime.device_state)
        self.assertEqual(self.runtime.device_state["PA0"], original_pin_state)

    def test_execute_io_invalid_i2c_payload_does_not_mutate_runtime_state(self) -> None:
        self.engine._device_runtime(self.runtime)
        original_bus_state = dict(self.runtime.device_state["i2c0"])

        with self.assertRaises(DomainError) as ctx:
            self.engine.execute_io(self.runtime, "i2c:transact", {"bus": "i2c0", "addr_7bit": "bad"})

        self.assertEqual(ctx.exception.error_code, "INVALID_I2C_ADDRESS")
        self.assertNotIn("i2c", self.runtime.device_state)
        self.assertEqual(self.runtime.device_state["i2c0"], original_bus_state)


if __name__ == "__main__":
    unittest.main()
