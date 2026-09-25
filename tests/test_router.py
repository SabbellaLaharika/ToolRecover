"""
Contract and Unit Tests for AI Function-Calling Router (Phase 6 / req-1 through req-8)
"""

import os
import pytest
from pydantic import ValidationError

os.environ["USE_OFFLINE_LLM"] = "true"

from src.tools import (
    FlightSearchInput, CalendarBookingInput, WeatherLookupInput, UnitConversionInput,
    FlightSearchOutput, WeatherLookupOutput, TOOLS
)
from src.fault_injector import FaultContext, inject_fault
from src.router import process_request



# ==========================================
# Requirement 1: Pydantic Tool Schemas
# ==========================================
def test_req1_pydantic_schemas_valid_and_invalid():
    # Valid FlightSearch
    valid_flight = FlightSearchInput(origin="MIA", destination="JFK", date="2024-10-10")
    assert valid_flight.origin == "MIA"
    assert valid_flight.date == "2024-10-10"

    # Invalid FlightSearch (bad date format raises ValidationError)
    with pytest.raises(ValidationError):
        FlightSearchInput(origin="MIA", destination="JFK", date="tomorrow")

    # Missing field FlightSearch raises ValidationError
    with pytest.raises(ValidationError):
        FlightSearchInput(origin="MIA", destination="JFK")

    # Invalid WeatherLookup enum unit raises ValidationError
    with pytest.raises(ValidationError):
        WeatherLookupInput(location="Tokyo", unit="INVALID_UNIT")


# ==========================================
# Requirement 2: Fault Injector Middleware
# ==========================================
def test_req2_fault_injector_timeout_and_malformed():
    # Test TIMEOUT fault
    FaultContext.set_fault("TIMEOUT")
    with pytest.raises(TimeoutError):
        TOOLS["WeatherLookup"]["function"](location="Tokyo", unit="C")

    # Test MALFORMED fault
    FaultContext.set_fault("MALFORMED")
    malformed_output = TOOLS["WeatherLookup"]["function"](location="Tokyo", unit="C")
    assert isinstance(malformed_output, dict)
    with pytest.raises(ValidationError):
        WeatherLookupOutput(**malformed_output)

    FaultContext.reset()


# ==========================================
# Requirement 3: Sunny Day Execution
# ==========================================
def test_req3_sunny_day_request():
    FaultContext.set_fault("NONE")
    res = process_request("Book a flight from MIA to JFK on 2024-10-10")
    assert res["status"] == "success"
    assert res["tool"] == "FlightSearch"
    assert res["attempts"] == 0
    assert "result" in res
    assert res["result"]["origin"] == "MIA"


# ==========================================
# Requirement 4: Missing Field Recovery Policy
# ==========================================
def test_req4_missing_field_recovery():
    FaultContext.set_fault("NONE")
    res = process_request("Book a flight to Paris tomorrow", use_recovery=True)
    assert res["status"] == "success"
    assert res["tool"] == "FlightSearch"
    assert res["attempts"] == 1


# ==========================================
# Requirement 5: Type Error Recovery Policy
# ==========================================
def test_req5_type_error_recovery():
    FaultContext.set_fault("NONE")
    res = process_request("Book a flight from MIA to JFK tomorrow", use_recovery=True)
    assert res["status"] == "success"
    assert res["tool"] == "FlightSearch"
    assert res["attempts"] == 1


# ==========================================
# Requirement 6: Timeout Backoff Recovery
# ==========================================
def test_req6_timeout_recovery_bounded_retry():
    FaultContext.set_fault("TIMEOUT")
    res = process_request("Get weather in Tokyo", use_recovery=True)
    # Under persistent TIMEOUT, retry 1 also times out -> returns explicit failure
    assert res["status"] == "error"
    assert res["reason"] == "timeout_unrecoverable"
    FaultContext.reset()


# ==========================================
# Requirement 7: Schema Repair Recovery Policy
# ==========================================
def test_req7_schema_repair_recovery():
    FaultContext.set_fault("MALFORMED")
    res = process_request("Get weather in Tokyo", use_recovery=True)
    assert res["status"] == "success"
    assert res["attempts"] == 2
    assert "result" in res
    FaultContext.reset()


# ==========================================
# Requirement 8: Explicit Structured Failure Object
# ==========================================
def test_req8_explicit_structured_failure():
    FaultContext.set_fault("TIMEOUT")
    res = process_request("Get weather in Tokyo", use_recovery=True)
    assert res["status"] == "error"
    assert "reason" in res
    assert res["reason"] == "timeout_unrecoverable"
    FaultContext.reset()
