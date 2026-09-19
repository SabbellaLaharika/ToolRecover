"""
Tool Schemas and Mock Implementations (Phase 1 / req-1-schemas)

Defines four tools using Pydantic models for input argument validation and output schema validation:
1. FlightSearch (origin, destination, date)
2. CalendarBooking (event_title, start_time, duration_minutes)
3. WeatherLookup (location, unit)
4. UnitConversion (value, from_unit, to_unit)
"""

from enum import Enum
import re
from datetime import datetime
from typing import Dict, Any, Type
from pydantic import BaseModel, Field, field_validator, ValidationError


# ==========================================
# 1. Weather Unit Enum
# ==========================================
class WeatherUnitEnum(str, Enum):
    C = "C"
    F = "F"


# ==========================================
# 2. Input Pydantic Models (Argument Validation)
# ==========================================
class FlightSearchInput(BaseModel):
    origin: str = Field(..., description="3-letter airport code or city name for departure")
    destination: str = Field(..., description="3-letter airport code or city name for arrival")
    date: str = Field(..., description="Departure date in ISO 8601 format (YYYY-MM-DD)")

    @field_validator("date")
    @classmethod
    def validate_iso_date(cls, value: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            raise ValueError(f"Invalid date format: '{value}'. Must be in ISO 8601 format (YYYY-MM-DD).")
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid calendar date: '{value}'. Must be a valid YYYY-MM-DD date.")
        return value


class CalendarBookingInput(BaseModel):
    event_title: str = Field(..., description="Title or description of the calendar event")
    start_time: str = Field(..., description="Start time in ISO format (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS)")
    duration_minutes: int = Field(..., description="Duration of the event in minutes", gt=0)

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: str) -> str:
        # Check standard ISO datetime patterns
        iso_patterns = [
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$",
            r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}(:\d{2})?$",
            r"^\d{4}-\d{2}-\d{2}$"
        ]
        if not any(re.match(p, value) for p in iso_patterns):
            raise ValueError(f"Invalid start_time format: '{value}'. Must be ISO-8601 formatted datetime.")
        return value


class WeatherLookupInput(BaseModel):
    location: str = Field(..., description="City or region name for weather lookup")
    unit: WeatherUnitEnum = Field(..., description="Temperature unit: 'C' or 'F'")


class UnitConversionInput(BaseModel):
    value: float = Field(..., description="Numeric value to convert")
    from_unit: str = Field(..., description="Source unit (e.g. km, miles, kg, lbs)")
    to_unit: str = Field(..., description="Target unit (e.g. miles, km, lbs, kg)")


# ==========================================
# 3. Output Pydantic Models (Response Validation)
# ==========================================
class FlightSearchOutput(BaseModel):
    status: str = Field("success", description="Status of the tool execution")
    flight_id: str = Field(..., description="Unique flight identification code")
    origin: str
    destination: str
    date: str
    price: float


class CalendarBookingOutput(BaseModel):
    status: str = Field("success", description="Status of the tool execution")
    booking_id: str = Field(..., description="Unique calendar booking confirmation ID")
    event_title: str
    start_time: str
    duration_minutes: int


class WeatherLookupOutput(BaseModel):
    status: str = Field("success", description="Status of the tool execution")
    location: str
    temperature: float
    unit: str
    condition: str


class UnitConversionOutput(BaseModel):
    status: str = Field("success", description="Status of the tool execution")
    converted_value: float
    from_unit: str
    to_unit: str


# ==========================================
# 4. Mock Tool Implementations
# ==========================================
def mock_flight_search(origin: str, destination: str, date: str) -> Dict[str, Any]:
    """Mock implementation for FlightSearch tool."""
    flight_hash = abs(hash(f"{origin}-{destination}-{date}")) % 9000 + 1000
    return {
        "status": "success",
        "flight_id": f"FL-{flight_hash}",
        "origin": origin.upper(),
        "destination": destination.upper(),
        "date": date,
        "price": 299.99
    }


def mock_calendar_booking(event_title: str, start_time: str, duration_minutes: int) -> Dict[str, Any]:
    """Mock implementation for CalendarBooking tool."""
    booking_hash = abs(hash(f"{event_title}-{start_time}")) % 90000 + 10000
    return {
        "status": "success",
        "booking_id": f"CAL-{booking_hash}",
        "event_title": event_title,
        "start_time": start_time,
        "duration_minutes": duration_minutes
    }


def mock_weather_lookup(location: str, unit: str) -> Dict[str, Any]:
    """Mock implementation for WeatherLookup tool."""
    temp = 22.5 if unit.upper() == "C" else 72.5
    return {
        "status": "success",
        "location": location.title(),
        "temperature": temp,
        "unit": unit.upper(),
        "condition": "Sunny with light breeze"
    }


def mock_unit_conversion(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """Mock implementation for UnitConversion tool."""
    # Simple deterministic mock conversion factor logic
    factor = 1.60934 if from_unit.lower() in ["mile", "miles"] and to_unit.lower() in ["km", "kilometer", "kilometers"] else 0.621371
    converted = round(value * factor, 4)
    return {
        "status": "success",
        "converted_value": converted,
        "from_unit": from_unit.lower(),
        "to_unit": to_unit.lower()
    }


# ==========================================
# 5. Tool Registry Mapping
# ==========================================
TOOLS = {
    "FlightSearch": {
        "input_model": FlightSearchInput,
        "output_model": FlightSearchOutput,
        "function": mock_flight_search,
        "description": "Search for flights given origin, destination, and date (YYYY-MM-DD)."
    },
    "CalendarBooking": {
        "input_model": CalendarBookingInput,
        "output_model": CalendarBookingOutput,
        "function": mock_calendar_booking,
        "description": "Book a calendar event given title, start time, and duration in minutes."
    },
    "WeatherLookup": {
        "input_model": WeatherLookupInput,
        "output_model": WeatherLookupOutput,
        "function": mock_weather_lookup,
        "description": "Get current weather given location and temperature unit ('C' or 'F')."
    },
    "UnitConversion": {
        "input_model": UnitConversionInput,
        "output_model": UnitConversionOutput,
        "function": mock_unit_conversion,
        "description": "Convert numerical values between units (value, from_unit, to_unit)."
    }
}
