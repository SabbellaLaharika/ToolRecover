"""
Fault Injection Middleware (Phase 2 / req-2-fault-injector)

Provides a deterministic fault injection mechanism for testing LLM tool recovery.
Supports directives:
- 'NONE': Normal pass-through tool execution.
- 'TIMEOUT': Sleeps briefly, then raises a TimeoutError.
- 'MALFORMED' or 'MALFORMED_RESPONSE': Executes tool, but alters the returned dictionary
  to violate the expected output Pydantic schema.
"""

import time
import functools
from typing import Callable, Any, Dict

class FaultContext:
    """Global/thread execution context for fault injection."""
    current_fault: str = "NONE"

    @classmethod
    def set_fault(cls, fault_type: str) -> None:
        """Set the active fault type: 'NONE', 'TIMEOUT', 'MALFORMED' / 'MALFORMED_RESPONSE'."""
        cls.current_fault = fault_type.upper()

    @classmethod
    def reset(cls) -> None:
        """Reset fault to 'NONE'."""
        cls.current_fault = "NONE"


def inject_fault(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for mock tools that intercepts execution based on FaultContext.current_fault.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        fault = FaultContext.current_fault.upper()

        if fault == "TIMEOUT":
            time.sleep(0.1)  # Brief sleep to simulate latency
            raise TimeoutError("Upstream service timed out")

        elif fault in ("MALFORMED", "MALFORMED_RESPONSE"):
            # Execute tool but corrupt/alter the output payload shape
            res = func(*args, **kwargs)
            if isinstance(res, dict):
                malformed = res.copy()
                # Remove status or required output fields to force output schema violation
                malformed.pop("status", None)
                malformed["msg"] = "success"
                
                # Tool specific corruptions
                if "temperature" in malformed:
                    malformed["temp_str"] = f"{malformed.pop('temperature')} degrees"
                if "flight_id" in malformed:
                    malformed["flight_id"] = 12345  # Int instead of required str
                if "booking_id" in malformed:
                    malformed.pop("booking_id")  # Missing required output field
                if "converted_value" in malformed:
                    malformed["converted_value"] = "invalid_float_string"
                
                return malformed
            return {"error": "malformed_payload", "data": "raw_corrupted_response"}

        # Normal execution (NONE)
        return func(*args, **kwargs)

    return wrapper
