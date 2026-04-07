from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lot.board.service import BoardServiceStub
from lot.contracts.errors import DomainError


class BoardServiceTests(unittest.TestCase):
    def test_load_profile_normalizes_supported_buses_and_gpio(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = root / "profiles" / "board.yaml"
            profile.parent.mkdir(parents=True, exist_ok=True)
            profile.write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "board: demo_board",
                        "buses:",
                        "  i2c0:",
                        "    pins:",
                        "      sda: PB7",
                        "      scl: PB6",
                        "    pullup_ohm: 4700",
                        "    devices:",
                        "      - addr_7bit: 0x48",
                        "        type: TMP102",
                        "  uart0:",
                        "    pins:",
                        "      tx: PA2",
                        "      rx: PA3",
                        "gpio:",
                        "  PA0:",
                        "    direction: output",
                    ]
                ),
                encoding="utf-8",
            )

            service = BoardServiceStub(root_dir=root)
            board = service.load_profile("profiles/board.yaml")

            self.assertEqual(board.board, "demo_board")
            self.assertEqual(board.version, "v1alpha1")
            self.assertEqual(board.buses["i2c0"]["kind"], "i2c")
            self.assertEqual(board.buses["i2c0"]["devices"][0]["addr_7bit"], 0x48)
            self.assertEqual(board.buses["uart0"]["baud"], 115200)
            self.assertEqual(board.gpio["PA0"]["direction"], "output")
            self.assertEqual(board.gpio["PA0"]["pull"], "none")

    def test_validate_reports_structured_errors(self) -> None:
        service = BoardServiceStub(root_dir=Path.cwd())
        errors = service.validate(
            {
                "version": "v1alpha1",
                "board": "demo_board",
                "buses": {
                    "i2c0": {
                        "pins": {"sda": "PB7", "scl": "PB7"},
                        "devices": [{"addr_7bit": 0x80, "type": ""}],
                    },
                    "uart0": {
                        "pins": {"tx": "PA2", "rx": "PA3"},
                        "baud": 0,
                    },
                },
                "gpio": {
                    "PB7": {"direction": "analog"},
                },
            }
        )

        error_codes = {item["error_code"] for item in errors}
        self.assertIn("REQUIRED_FIELD_MISSING", error_codes)
        self.assertIn("DUPLICATE_PIN_ASSIGNMENT", error_codes)
        self.assertIn("INVALID_I2C_ADDRESS", error_codes)
        self.assertIn("INVALID_UART_BAUD", error_codes)
        self.assertIn("INVALID_GPIO_DIRECTION", error_codes)

    def test_load_profile_raises_domain_error_for_invalid_payload(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = root / "invalid.yaml"
            profile.write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "board: demo_board",
                        "buses:",
                        "  spi0:",
                        "    pins:",
                        "      mosi: PA11",
                        "      miso: PA12",
                    ]
                ),
                encoding="utf-8",
            )

            service = BoardServiceStub(root_dir=root)
            with self.assertRaises(DomainError) as ctx:
                service.load_profile("invalid.yaml")

            self.assertEqual(ctx.exception.error_code, "BOARD_PROFILE_INVALID")
            self.assertTrue(ctx.exception.details["errors"])

    def test_load_profile_rejects_duplicate_yaml_keys(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profile = root / "duplicate.yaml"
            profile.write_text(
                "\n".join(
                    [
                        "version: v1alpha1",
                        "board: demo_board",
                        "buses:",
                        "  i2c0:",
                        "    pins:",
                        "      sda: PB7",
                        "      scl: PB6",
                        "  i2c0:",
                        "    pins:",
                        "      sda: PB9",
                        "      scl: PB8",
                    ]
                ),
                encoding="utf-8",
            )

            service = BoardServiceStub(root_dir=root)
            with self.assertRaises(DomainError) as ctx:
                service.load_profile("duplicate.yaml")

            self.assertEqual(ctx.exception.error_code, "BOARD_PROFILE_PARSE_ERROR")


if __name__ == "__main__":
    unittest.main()
