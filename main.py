from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fast_flights import FlightData, Passengers, get_flights
from fast_flights.flights_impl import TFSData
import re

app = FastAPI(title="Fast Flights API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def google_flights_url(flight_legs: list, trip: str, seat: str, passengers: Passengers) -> str:
    tfs = TFSData.from_interface(
        flight_data=flight_legs,
        trip=trip,
        seat=seat,
        passengers=passengers,
    )
    tfs_param = tfs.as_b64().decode("utf-8")
    return f"https://www.google.com/travel/flights?tfs={tfs_param}&hl=en&tfu=EgQIABABIgA"


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/flights")
def search_flights(
    from_airport: str = Query(..., description="IATA departure airport code (e.g. LAX)"),
    to_airport: str = Query(..., description="IATA arrival airport code (e.g. JFK)"),
    date: str = Query(..., description="Departure date in YYYY-MM-DD format"),
    return_date: Optional[str] = Query(None, description="Return date in YYYY-MM-DD format (required for round-trip)"),
    trip: Literal["one-way", "round-trip", "multi-city"] = Query("one-way"),
    seat: Literal["economy", "premium-economy", "business", "first"] = Query("economy"),
    adults: int = Query(1, ge=1, le=9),
    children: int = Query(0, ge=0, le=9),
    infants_in_seat: int = Query(0, ge=0, le=9),
    infants_on_lap: int = Query(0, ge=0, le=9),
    max_stops: Optional[int] = Query(None, ge=0, le=3, description="Max stops (0 = nonstop)"),
    fetch_mode: Literal["common", "fallback", "force-fallback", "local"] = Query("local"),
):
    if not DATE_RE.match(date):
        raise HTTPException(status_code=422, detail="date must be in YYYY-MM-DD format")

    if trip == "round-trip":
        if not return_date:
            raise HTTPException(status_code=422, detail="return_date is required for round-trip")
        if not DATE_RE.match(return_date):
            raise HTTPException(status_code=422, detail="return_date must be in YYYY-MM-DD format")
        if return_date <= date:
            raise HTTPException(status_code=422, detail="return_date must be after date")

    total_passengers = adults + children + infants_in_seat + infants_on_lap
    if total_passengers > 9:
        raise HTTPException(status_code=422, detail="Total passengers cannot exceed 9")
    if infants_on_lap > adults:
        raise HTTPException(status_code=422, detail="infants_on_lap cannot exceed number of adults")

    origin = from_airport.upper()
    destination = to_airport.upper()

    flight_legs = [FlightData(date=date, from_airport=origin, to_airport=destination, max_stops=max_stops)]
    if trip == "round-trip":
        flight_legs.append(FlightData(date=return_date, from_airport=destination, to_airport=origin, max_stops=max_stops))

    passengers = Passengers(
        adults=adults,
        children=children,
        infants_in_seat=infants_in_seat,
        infants_on_lap=infants_on_lap,
    )

    try:
        result = get_flights(
            flight_data=flight_legs,
            trip=trip,
            seat=seat,
            passengers=passengers,
            fetch_mode=fetch_mode,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "price_level": result.current_price,
        "book_url": google_flights_url(flight_legs, trip, seat, passengers),
        "flights": [
            {
                "name": f.name,
                "price": f.price,
                "departure": f.departure,
                "arrival": f.arrival,
                "arrival_time_ahead": f.arrival_time_ahead,
                "duration": f.duration,
                "stops": f.stops,
                "delay": f.delay,
                "is_best": f.is_best,
            }
            for f in result.flights
        ],
    }
