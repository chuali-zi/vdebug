from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, ValidationError

from lot.contracts.errors import DomainError
from lot.contracts.models import BoardProfile, StrictModel


class _BoardDocument(StrictModel):
    version: str
    board: str
    buses: dict[str, dict[str, Any]] = Field(default_factory=dict)
    gpio: dict[str, dict[str, Any]] = Field(default_factory=dict)
    power: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None


class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(slots=True)
class _BoardAnalysis:
    normalized: dict[str, Any]
    errors: list[dict[str, Any]]


@dataclass(slots=True)
class BoardServiceStub:
    """Loads and normalizes board profile documents."""

    root_dir: Path

    def load_profile(self, profile_ref: str | Path) -> BoardProfile:
        candidate, raw = self._load_raw_profile(profile_ref)
        normalized = self.normalize(raw)
        return BoardProfile(
            source_path=str(candidate),
            version=normalized["version"],
            board=normalized["board"],
            buses=normalized["buses"],
            gpio=normalized["gpio"],
            power=normalized["power"],
            constraints=normalized["constraints"],
            raw=raw,
        )

    def load(self, board_profile_ref: str | Path) -> dict[str, Any]:
        _, raw = self._load_raw_profile(board_profile_ref)
        return self.normalize(raw)

    def validate(self, raw_payload: dict[str, Any]) -> list[dict[str, Any]]:
        return self._inspect(raw_payload).errors

    def normalize(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        analysis = self._inspect(raw_payload)
        if analysis.errors:
            raise self._invalid_profile_error(analysis.errors)
        return analysis.normalized

    def _load_raw_profile(self, profile_ref: str | Path) -> tuple[Path, dict[str, Any]]:
        candidate = Path(profile_ref)
        if not candidate.is_absolute():
            candidate = self.root_dir / candidate
        candidate = candidate.resolve()

        if not candidate.exists():
            raise DomainError(
                error_code="BOARD_PROFILE_NOT_FOUND",
                message=f"Board profile not found: {candidate}",
                explain="The requested board profile file could not be resolved from the repository root.",
            )

        try:
            loaded = yaml.load(candidate.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
        except yaml.YAMLError as exc:
            raise DomainError(
                error_code="BOARD_PROFILE_PARSE_ERROR",
                message=f"Failed to parse board profile: {candidate}",
                explain="The board profile YAML is malformed or contains duplicate mapping keys.",
                observations=[str(exc)],
                details={"source_path": str(candidate)},
            ) from exc

        if loaded is None:
            loaded = {}

        if not isinstance(loaded, dict):
            raise DomainError(
                error_code="BOARD_PROFILE_INVALID",
                message=f"Board profile root must be a mapping: {candidate}",
                explain="The board profile file must deserialize to a YAML mapping at the top level.",
                details={
                    "source_path": str(candidate),
                    "errors": [
                        self._error(
                            path="$",
                            error_code="INVALID_TYPE",
                            message="Board profile root must be a mapping object.",
                        )
                    ],
                },
            )

        return candidate, loaded

    def _inspect(self, raw_payload: dict[str, Any]) -> _BoardAnalysis:
        errors: list[dict[str, Any]] = []
        if not isinstance(raw_payload, dict):
            return _BoardAnalysis(
                normalized={},
                errors=[
                    self._error(
                        path="$",
                        error_code="INVALID_TYPE",
                        message="Board profile payload must be a mapping object.",
                    )
                ],
            )

        try:
            document = _BoardDocument.model_validate(raw_payload)
        except ValidationError as exc:
            return _BoardAnalysis(normalized={}, errors=self._pydantic_errors(exc))

        normalized_buses: dict[str, Any] = {}
        normalized_gpio: dict[str, Any] = {}
        claimed_pins: dict[str, str] = {}

        version = document.version.strip()
        board = document.board.strip()
        if not version:
            errors.append(
                self._error(
                    path="version",
                    error_code="REQUIRED_FIELD_MISSING",
                    message="version must not be empty.",
                )
            )
        if not board:
            errors.append(
                self._error(
                    path="board",
                    error_code="REQUIRED_FIELD_MISSING",
                    message="board must not be empty.",
                )
            )

        for bus_name, bus_payload in document.buses.items():
            normalized_bus_name = str(bus_name).strip()
            bus_path = f"buses.{bus_name}"
            if not normalized_bus_name:
                errors.append(
                    self._error(
                        path=bus_path,
                        error_code="INVALID_BUS_NAME",
                        message="Bus names must be non-empty strings.",
                    )
                )
                continue
            if normalized_bus_name in normalized_buses:
                errors.append(
                    self._error(
                        path=bus_path,
                        error_code="DUPLICATE_BUS_NAME",
                        message=f"Bus name {normalized_bus_name!r} is duplicated after normalization.",
                    )
                )
                continue

            bus_kind = self._infer_bus_kind(normalized_bus_name, bus_payload)
            if bus_kind == "i2c":
                normalized_bus = self._validate_i2c_bus(
                    normalized_bus_name,
                    bus_payload,
                    bus_path,
                    claimed_pins,
                    errors,
                )
            elif bus_kind == "uart":
                normalized_bus = self._validate_uart_bus(
                    normalized_bus_name,
                    bus_payload,
                    bus_path,
                    claimed_pins,
                    errors,
                )
            else:
                errors.append(
                    self._error(
                        path=bus_path,
                        error_code="UNSUPPORTED_BUS_TYPE",
                        message=(
                            f"Unsupported bus {normalized_bus_name!r}. MVP only supports I2C and UART buses."
                        ),
                    )
                )
                continue

            if normalized_bus is not None:
                normalized_buses[normalized_bus_name] = normalized_bus

        for pin_name, pin_payload in document.gpio.items():
            normalized_pin_name = str(pin_name).strip()
            pin_path = f"gpio.{pin_name}"
            if not normalized_pin_name:
                errors.append(
                    self._error(
                        path=pin_path,
                        error_code="INVALID_PIN_NAME",
                        message="GPIO pin names must be non-empty strings.",
                    )
                )
                continue
            if normalized_pin_name in normalized_gpio:
                errors.append(
                    self._error(
                        path=pin_path,
                        error_code="DUPLICATE_PIN_ASSIGNMENT",
                        message=f"GPIO pin {normalized_pin_name!r} is duplicated after normalization.",
                    )
                )
                continue
            if not isinstance(pin_payload, dict):
                errors.append(
                    self._error(
                        path=pin_path,
                        error_code="INVALID_TYPE",
                        message="GPIO entries must be mapping objects.",
                    )
                )
                continue

            self._check_unknown_fields(
                payload=pin_payload,
                allowed_fields={"direction", "pull"},
                path=pin_path,
                errors=errors,
            )
            self._claim_pin(normalized_pin_name, pin_path, claimed_pins, errors)

            direction = str(pin_payload.get("direction", "input")).strip().lower()
            pull = str(pin_payload.get("pull", "none")).strip().lower()

            if direction not in {"input", "output", "inout"}:
                errors.append(
                    self._error(
                        path=f"{pin_path}.direction",
                        error_code="INVALID_GPIO_DIRECTION",
                        message="GPIO direction must be one of: input, output, inout.",
                    )
                )
            if pull not in {"none", "up", "down"}:
                errors.append(
                    self._error(
                        path=f"{pin_path}.pull",
                        error_code="INVALID_GPIO_PULL",
                        message="GPIO pull must be one of: none, up, down.",
                    )
                )

            normalized_gpio[normalized_pin_name] = {
                "direction": direction,
                "pull": pull,
            }

        normalized = {
            "version": version,
            "board": board,
            "buses": normalized_buses,
            "gpio": normalized_gpio,
            "power": dict(document.power) if document.power is not None else None,
            "constraints": dict(document.constraints) if document.constraints is not None else None,
        }
        return _BoardAnalysis(normalized=normalized, errors=errors)

    def _validate_i2c_bus(
        self,
        bus_name: str,
        bus_payload: dict[str, Any],
        bus_path: str,
        claimed_pins: dict[str, str],
        errors: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        self._check_unknown_fields(
            payload=bus_payload,
            allowed_fields={"pins", "pullup_ohm", "devices"},
            path=bus_path,
            errors=errors,
        )
        pins = bus_payload.get("pins")
        if not isinstance(pins, dict):
            errors.append(
                self._error(
                    path=f"{bus_path}.pins",
                    error_code="INVALID_TYPE",
                    message="I2C bus pins must be a mapping with sda and scl.",
                )
            )
            return None

        normalized_pins: dict[str, str] = {}
        for role in ("sda", "scl"):
            pin_value = pins.get(role)
            if not isinstance(pin_value, str) or not pin_value.strip():
                errors.append(
                    self._error(
                        path=f"{bus_path}.pins.{role}",
                        error_code="REQUIRED_FIELD_MISSING",
                        message=f"I2C pin {role} must be a non-empty string.",
                    )
                )
                continue
            normalized_pin = pin_value.strip()
            normalized_pins[role] = normalized_pin
            self._claim_pin(normalized_pin, f"{bus_path}.pins.{role}", claimed_pins, errors)

        pullup_ohm = bus_payload.get("pullup_ohm")
        if pullup_ohm is not None and (not isinstance(pullup_ohm, int) or pullup_ohm <= 0):
            errors.append(
                self._error(
                    path=f"{bus_path}.pullup_ohm",
                    error_code="INVALID_I2C_PULLUP",
                    message="I2C pullup_ohm must be a positive integer when provided.",
                )
            )

        devices = bus_payload.get("devices", [])
        if not isinstance(devices, list):
            errors.append(
                self._error(
                    path=f"{bus_path}.devices",
                    error_code="INVALID_TYPE",
                    message="I2C devices must be a list of device definitions.",
                )
            )
            devices = []

        normalized_devices: list[dict[str, Any]] = []
        for index, device_payload in enumerate(devices):
            device_path = f"{bus_path}.devices[{index}]"
            if not isinstance(device_payload, dict):
                errors.append(
                    self._error(
                        path=device_path,
                        error_code="INVALID_TYPE",
                        message="Each I2C device must be a mapping object.",
                    )
                )
                continue

            self._check_unknown_fields(
                payload=device_payload,
                allowed_fields={"addr_7bit", "type"},
                path=device_path,
                errors=errors,
            )

            addr = device_payload.get("addr_7bit")
            normalized_addr = self._parse_int(addr)
            if normalized_addr is None or not 0 <= normalized_addr <= 0x7F:
                errors.append(
                    self._error(
                        path=f"{device_path}.addr_7bit",
                        error_code="INVALID_I2C_ADDRESS",
                        message="I2C addr_7bit must be an integer in the 7-bit range 0..127.",
                    )
                )
            device_type = device_payload.get("type")
            if not isinstance(device_type, str) or not device_type.strip():
                errors.append(
                    self._error(
                        path=f"{device_path}.type",
                        error_code="REQUIRED_FIELD_MISSING",
                        message="I2C device type must be a non-empty string.",
                    )
                )
                normalized_type = ""
            else:
                normalized_type = device_type.strip()

            normalized_devices.append(
                {
                    "type": normalized_type,
                    "addr_7bit": normalized_addr,
                }
            )

        return {
            "kind": "i2c",
            "pins": normalized_pins,
            "pullup_ohm": pullup_ohm,
            "devices": normalized_devices,
        }

    def _validate_uart_bus(
        self,
        bus_name: str,
        bus_payload: dict[str, Any],
        bus_path: str,
        claimed_pins: dict[str, str],
        errors: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        self._check_unknown_fields(
            payload=bus_payload,
            allowed_fields={"pins", "baud"},
            path=bus_path,
            errors=errors,
        )
        pins = bus_payload.get("pins")
        if not isinstance(pins, dict):
            errors.append(
                self._error(
                    path=f"{bus_path}.pins",
                    error_code="INVALID_TYPE",
                    message="UART bus pins must be a mapping with tx and rx.",
                )
            )
            return None

        normalized_pins: dict[str, str] = {}
        for role in ("tx", "rx"):
            pin_value = pins.get(role)
            if not isinstance(pin_value, str) or not pin_value.strip():
                errors.append(
                    self._error(
                        path=f"{bus_path}.pins.{role}",
                        error_code="REQUIRED_FIELD_MISSING",
                        message=f"UART pin {role} must be a non-empty string.",
                    )
                )
                continue
            normalized_pin = pin_value.strip()
            normalized_pins[role] = normalized_pin
            self._claim_pin(normalized_pin, f"{bus_path}.pins.{role}", claimed_pins, errors)

        baud = bus_payload.get("baud", 115200)
        if not isinstance(baud, int) or baud <= 0:
            errors.append(
                self._error(
                    path=f"{bus_path}.baud",
                    error_code="INVALID_UART_BAUD",
                    message="UART baud must be a positive integer.",
                )
            )

        return {
            "kind": "uart",
            "pins": normalized_pins,
            "baud": baud,
        }

    def _infer_bus_kind(self, bus_name: str, bus_payload: dict[str, Any]) -> str | None:
        lowered = bus_name.lower()
        if lowered.startswith("i2c"):
            return "i2c"
        if lowered.startswith("uart"):
            return "uart"

        pins = bus_payload.get("pins", {})
        if isinstance(pins, dict) and {"sda", "scl"}.issubset(pins):
            return "i2c"
        if isinstance(pins, dict) and {"tx", "rx"}.issubset(pins):
            return "uart"
        return None

    def _claim_pin(
        self,
        pin_name: str,
        owner_path: str,
        claimed_pins: dict[str, str],
        errors: list[dict[str, Any]],
    ) -> None:
        existing_owner = claimed_pins.get(pin_name)
        if existing_owner and existing_owner != owner_path:
            errors.append(
                self._error(
                    path=owner_path,
                    error_code="DUPLICATE_PIN_ASSIGNMENT",
                    message=f"Pin {pin_name!r} is already assigned to {existing_owner}.",
                    details={"pin": pin_name, "claimed_by": existing_owner},
                )
            )
            return
        claimed_pins[pin_name] = owner_path

    def _check_unknown_fields(
        self,
        payload: dict[str, Any],
        allowed_fields: set[str],
        path: str,
        errors: list[dict[str, Any]],
    ) -> None:
        for field_name in payload:
            if field_name not in allowed_fields:
                errors.append(
                    self._error(
                        path=f"{path}.{field_name}",
                        error_code="UNKNOWN_FIELD",
                        message=f"Field {field_name!r} is not supported in the MVP board schema.",
                    )
                )

    def _invalid_profile_error(self, errors: list[dict[str, Any]]) -> DomainError:
        return DomainError(
            error_code="BOARD_PROFILE_INVALID",
            message="Board profile validation failed.",
            explain="The board profile does not satisfy the MVP board schema.",
            observations=[f"{item['path']}: {item['message']}" for item in errors[:5]],
            details={"errors": errors},
        )

    def _pydantic_errors(self, exc: ValidationError) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        for item in exc.errors(include_url=False):
            path = ".".join(str(part) for part in item["loc"]) or "$"
            error_code = "REQUIRED_FIELD_MISSING" if item["type"] == "missing" else "INVALID_TYPE"
            errors.append(
                self._error(
                    path=path,
                    error_code=error_code,
                    message=item["msg"],
                )
            )
        return errors

    def _parse_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            base = 16 if text.lower().startswith("0x") else 10
            try:
                return int(text, base)
            except ValueError:
                return None
        return None

    def _error(
        self,
        *,
        path: str,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "path": path,
            "error_code": error_code,
            "message": message,
        }
        if details:
            payload["details"] = details
        return payload
