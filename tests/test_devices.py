from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lot.board.service import BoardServiceStub
from lot.devices.registry import DeviceRuntime, build_default_device_registry
from lot.engine.service import EngineServiceStub
from lot.session.models import RuntimeContext


class DeviceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        board_service = BoardServiceStub(root_dir=Path.cwd())
        cls.board_profile = board_service.load_profile("profiles/example_stm32f4.yaml")

    def setUp(self) -> None:
        self.registry = build_default_device_registry()
        self.device_runtime = DeviceRuntime(
            registry=self.registry,
            session_id="sess-test",
            storage={"devices": {}, "state": {}},
        )
        self.device_runtime.register_from_board(self.board_profile)

    def test_register_from_board_builds_serializable_runtime_snapshot(self) -> None:
        snapshot = self.device_runtime.snapshot()

        self.assertIn("PA0", snapshot["devices"])
        self.assertIn("PA1", snapshot["devices"])
        self.assertIn("uart0", snapshot["devices"])
        self.assertIn("i2c0", snapshot["devices"])
        self.assertFalse(snapshot["state"]["PA0"]["value"])
        self.assertTrue(snapshot["state"]["PA1"]["value"])

    def test_gpio_write_read_and_direction_conflict_fault(self) -> None:
        write_result = self.device_runtime.execute(
            "gpio:set",
            {"pin": "PA0", "value": True},
            now_ns=10,
        )
        self.assertTrue(write_result["result"]["accepted"])
        self.assertEqual(write_result["events"][0].type, "GPIO_WRITE")

        read_result = self.device_runtime.execute(
            "gpio:get",
            {"pin": "PA0"},
            now_ns=11,
        )
        self.assertTrue(read_result["result"]["value"])

        self.device_runtime.inject_fault(
            "gpio_direction_conflict",
            {"pin": "PA0"},
            now_ns=12,
        )
        blocked_result = self.device_runtime.execute(
            "gpio:set",
            {"pin": "PA0", "value": False},
            now_ns=13,
        )
        self.assertFalse(blocked_result["result"]["accepted"])
        self.assertEqual(blocked_result["events"][0].type, "GPIO_DIRECTION_CONFLICT")

    def test_i2c_transaction_and_fault_injection_are_stable(self) -> None:
        ok_result = self.device_runtime.execute(
            "i2c:transact",
            {"bus": "i2c0", "addr_7bit": 0x48, "write": [0x01], "read_len": 2},
            now_ns=20,
        )
        self.assertTrue(ok_result["result"]["accepted"])
        self.assertEqual(ok_result["events"][0].type, "I2C_TRANSACTION")
        self.assertEqual(len(ok_result["result"]["read"]), 2)

        self.device_runtime.inject_fault(
            "repeated_nack",
            {"bus": "i2c0", "count": 1},
            now_ns=21,
        )
        nack_result = self.device_runtime.execute(
            "i2c:transact",
            {"bus": "i2c0", "addr_7bit": 0x48, "write": [0x02]},
            now_ns=22,
        )
        self.assertFalse(nack_result["result"]["accepted"])
        self.assertEqual(nack_result["events"][0].type, "I2C_NACK")

        self.device_runtime.inject_fault(
            "i2c_sda_stuck_low",
            {"bus": "i2c0"},
            now_ns=23,
        )
        stuck_result = self.device_runtime.execute(
            "i2c:transact",
            {"bus": "i2c0", "addr_7bit": 0x48, "write": []},
            now_ns=24,
        )
        self.assertFalse(stuck_result["result"]["accepted"])
        self.assertEqual(stuck_result["events"][0].type, "I2C_BUS_STUCK_LOW")

    def test_engine_execute_io_delegates_to_devices_runtime(self) -> None:
        runtime = RuntimeContext.from_board_profile(
            session_id="sess-engine",
            board_profile=self.board_profile,
        )
        engine = EngineServiceStub(device_registry=self.registry)

        io_result = engine.execute_io(
            runtime,
            "gpio:set",
            {"pin": "PA0", "value": True},
        )

        self.assertTrue(io_result.result["accepted"])
        self.assertEqual(io_result.events[0].type, "GPIO_SET")
        self.assertTrue(runtime.device_state["PA0"]["value"])


if __name__ == "__main__":
    unittest.main()
