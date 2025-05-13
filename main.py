from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import base64
import uvicorn
import asyncio
import logging
import os
from datetime import datetime
import calendar
from parser import KoeriParser
from typing import Optional
from load_dotenv import load_dotenv

load_dotenv()

LOGGING = bool(str(os.getenv("LOGGING")))

if LOGGING == True:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger(__name__)

app = FastAPI(
    title="KOERI Earthquake Data API",
    description="API for accessing earthquake data from the Kandilli Observatory and Earthquake Research Institute (KOERI)",
    version="1.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the parser
parser = None

def get_parser():
    global parser
    if parser is None:
        parser = KoeriParser()
    return parser

async def refresh_earthquake_data():
    """Background task that refreshes earthquake data at regular intervals"""
    parser = get_parser()
    try:
        earthquakes = parser.get_earthquakes()
        new_records = parser.save_to_database(earthquakes)
        logger.info(f"Data refreshed automatically: {len(earthquakes)} fetched, {new_records} new records")
        return {
            "status": "success",
            "message": "Data refreshed successfully",
            "earthquakes_fetched": len(earthquakes),
            "new_records_inserted": new_records,
        }
    except Exception as e:
        logger.error(f"Failed to refresh data: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to refresh data: {str(e)}",
        }

async def polling_service():
    """Background service that polls for new data at regular intervals"""
    # Get interval from environment variable (in seconds)
    # Default to 1 hour if not specified
    try:
        poll_interval = int(os.getenv("POLL_INTERVAL", "3600"))
    except ValueError:
        poll_interval = 3600
        logger.warning("Invalid POLL_INTERVAL value, using default of 3600 seconds")

    logger.info(f"Starting earthquake data polling service (interval: {poll_interval} seconds)")

    while True:
        try:
            await refresh_earthquake_data()
        except Exception as e:
            logger.error(f"Error in polling service: {str(e)}")

        # Wait for the next interval
        await asyncio.sleep(poll_interval)

@app.on_event("startup")
async def startup_event():
    """Start the polling service when the application starts"""
    global polling_task
    polling_task = asyncio.create_task(polling_service())
    logger.info("Earthquake data polling service started")

@app.get("/", tags=["Info"])
async def root():
    """Root endpoint providing API information"""
    return {
        "name": "KOERI Earthquake Data API",
        "version": "1.1.3",
        "description": "API for accessing earthquake data from Kandilli Observatory and Earthquake Research Institute",
        "database": "SQLite",
        "endpoints": {
            "GET /docs": "Swagger based documentation page for API usage",
            "GET /stats": "Get statistics about the earthquake database",
            "GET /earthquakes/latest": "Get the latest earthquake data",
            "GET /earthquakes/day/{date}": "Get earthquake data for a specific date",
            "GET /earthquakes/week/{year}/{week}": "Get earthquake data for a specific week",
            "GET /earthquakes/month/{year}/{month}": "Get earthquake data for a specific month",
            "GET /earthquakes/search": "Search earthquake data based on various criteria"
        }
    }

@app.get("/polling/status", tags=["System"])
async def polling_status():
    """
    Get the status of the polling service

    Returns:
        Information about the polling service
    """
    try:
        poll_interval = int(os.getenv("POLL_INTERVAL", "3600"))
    except ValueError:
        poll_interval = 3600

    return {
        "status": "active" if polling_task and not polling_task.done() else "inactive",
        "polling_interval": poll_interval,
        "polling_interval_human": f"{poll_interval // 60} minutes {poll_interval % 60} seconds",
        "next_poll_in": "unknown"
    }

@app.get("/earthquakes/latest", tags=["Earthquakes"])
async def get_latest_earthquakes(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    parser: KoeriParser = Depends(get_parser)
):
    """
    Get the latest earthquake data

    Args:
        limit: Maximum number of records to return (1-1000)

    Returns:
        List of latest earthquake records
    """
    try:
        earthquakes = parser.get_latest_earthquakes(limit)
        return {
            "count": len(earthquakes),
            "data": earthquakes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest data: {str(e)}")

@app.get("/earthquakes/day/{date}", tags=["Earthquakes"])
async def get_earthquakes_by_day(
    date: str,
    parser: KoeriParser = Depends(get_parser)
):
    """
    Get earthquake data for a specific date

    Args:
        date: Date in YYYY-MM-DD format

    Returns:
        List of earthquake records for the specified date
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        earthquakes = parser.get_earthquake_for_date(date)
        return {
            "date": date,
            "count": len(earthquakes),
            "data": earthquakes
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for date {date}: {str(e)}")

@app.get("/earthquakes/week/{year}/{week}", tags=["Earthquakes"])
async def get_earthquakes_by_week(
    year: int,
    week: int,
    parser: KoeriParser = Depends(get_parser)
):
    """
    Get earthquake data for a specific week

    Args:
        year: Year (e.g., 2023)
        week: Week number (1-53)

    Returns:
        List of earthquake records for the specified week
    """
    try:
        # Validate week number
        if week < 1 or week > 53:
            raise HTTPException(status_code=400, detail="Week number must be between 1 and 53")

        earthquakes = parser.get_earthquakes_for_week(year, week)
        return {
            "year": year,
            "week": week,
            "count": len(earthquakes),
            "data": earthquakes
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch data for year {year}, week {week}: {str(e)}"
        )

@app.get("/earthquakes/month/{year}/{month}", tags=["Earthquakes"])
async def get_earthquakes_by_month(
    year: int,
    month: int,
    parser: KoeriParser = Depends(get_parser)
):
    """
    Get earthquake data for a specific month

    Args:
        year: Year (e.g., 2023)
        month: Month number (1-12)

    Returns:
        List of earthquake records for the specified month
    """
    try:
        # Validate month number
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

        earthquakes = parser.get_earthquakes_for_month(year, month)
        return {
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "count": len(earthquakes),
            "data": earthquakes
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch data for year {year}, month {month}: {str(e)}"
        )

@app.get("/earthquakes/search", tags=["Earthquakes"])
async def search_earthquakes(
    min_magnitude: Optional[float] = Query(None, description="Minimum magnitude"),
    max_magnitude: Optional[float] = Query(None, description="Maximum magnitude"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    location: Optional[str] = Query(None, description="Location keyword (e.g. city name)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    parser: KoeriParser = Depends(get_parser)
):
    """
    Search for earthquakes based on various criteria

    Returns:
        List of matching earthquake records
    """
    try:
        # Validate date formats if provided
        if start_date:
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

        earthquakes = parser.search_earthquakes(
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            start_date=start_date,
            end_date=end_date,
            location_keyword=location,
            limit=limit
        )

        return {
            "count": len(earthquakes),
            "filters": {
                "min_magnitude": min_magnitude,
                "max_magnitude": max_magnitude,
                "start_date": start_date,
                "end_date": end_date,
                "location": location
            },
            "data": earthquakes
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search earthquakes: {str(e)}")

@app.get("/stats", tags=["System"])
async def get_database_stats(parser: KoeriParser = Depends(get_parser)):
    """
    Get statistics about the earthquake database

    Returns:
        Database statistics
    """
    try:
        return parser.get_database_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database statistics: {str(e)}")

@app.get("/health", tags=["System"])
async def health_check(parser: KoeriParser = Depends(get_parser)):
    """
    Health check endpoint

    Returns:
        Health status of the API
    """
    try:
        stats = parser.get_database_stats()
        return {
            "status": "healthy",
            "database": {
                "total_records": stats["total_earthquakes"],
                "date_range": stats["date_range"]
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle all uncaught exceptions"""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application shuts down"""
    global parser, polling_task

    # Cancel the polling task
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            logger.info("Polling service cancelled")

    # Close the parser
    if parser:
        parser.close()
        parser = None
        logger.info("Parser closed")

FAVICON_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAG2ElEQVRogd3af6xWdR0H8NdzufdcRcHSQCHI/rAWZ5kWY1lUWC2X/cBaWW0tHC0SxTSc1LDmWtova5pT0yXNmNXWcqMkVCRcUPYTVDJPguQPiEAU5YeI9wD36Y/7eS4PD8+P8zzPZW69t2fjnvM93/N5f7/fz6/3gf8TlEZiklzah1PxFkzDDEzEKeivGjqAbdiC32MN1mFTIjvQjQ0dExmQlkqMw7vwMUwP449pY5p9QWo1foM/J7JnO7GnIyK5dHwY/3mc0abxjbAP/8AiLElkO9p5uC0iubQf52JBHKG+ts0t8hr+hGuxMpHlRR4qTCSXTsaV+Axe1ZWpxbADP8UPEtm2VoNbEglfeCuuD3/oGTFTW+MgVuKKRPZIs4FNieTSnohAP4yI9EqgjIcwt8yaflm53qCGqzsgLeFs/OQVJCEW+21YVGJqs0F1kUvPwB04/SgZuA//xnYcwPF4HU4cNoH9GB2/Eh7ErET2aCEiuXRCkHj/USAwgOWx03/F7jg+vXgtxlcRzfEeXIMTYtwyzE5kzzUlEiH2O7gUo0aYxM4w6rZEtrvZwLDjfCzElCpb9+M6XFUdmuv5yDmYfRRI7MbXcWMBEmPxDfwIac2C9+ELEYSG0VMzwTh85Sjkif24KXaiaYILEldjPsY0GHYSrsilw3YOE4ko9Um8fSQZBFbhugIk+nAJ5tYUm/UwAzMrfwwTKQ2xnHUUyo4XcG3B2ml67ERSYGw/Phc7eNjROttQBh9pLMMfWw3KpSfiq3hNG3OfhXeoEMmlCc4rsJ3tYmf4xb5mg+L9X8R725z/eMzMpaN648KkqKNGGquwttmAXHpc+MTCDhfyfZhUITIFEzqztSH2485EtrfRgFw6MULyBZG9O8FkvLlCZFqD1cijfBCxvC8ycBFsiHa2LnLpG3AjPtBlRT0a03ojg9aG3IexGE9E1BEJ8hSMDUKnxRmdHOXDhKiTjon7y/HfBiTGR1twzgjoBiXM6A1jTq65uQ63JLKBZjNEr9Ifhp8UZCZGzXRfIhusQ2IU5kWELI+QAPL6XhxXVXFW8HGsyaWLEtnLjZ6O3uDl+O3BUwVeOjWi09X4fixkt5jQE+ezdlXG4tu4PpemsYpdI47xPDwQnd8LBR4rgv6eONP1MumYiO1344ZcOj2XjolSplNMi7L8bmwNHxwR9GAwfo3un4qLsRRLS8zPpdNy6QntkIpd/RSeQVZmb8g/I4LeaHRaqXwlvDoKtXdjF7ISq3Lpquipd9Rz7ipMwgfxyzLP98vKufThWMSuBY3emOhgG8/0BKnp8fsyHsPKXLoEaxLZ/jrPnRVBZWWVgPAYXgyf7AZ7eqLh6UimDIwOcWBByJ4Lw6mHEbXUR5HF7lWwuct3V/BMD17Cf0ZgMoa04Jl1GqLTo/+/qzy0cBVsD3LdIuuJY/BAJKdusQXfxPOVC7n0WFwYeWZJtS4VCbdbhx/E6oqTPRQ70w02R45YVnH6EPjOCxHhzgYJ89E2fbQWe7C2QmQ9nu5wojIewRwsTWQHHSJxbojRG3Fr5V4NHnf4cWsXG5BViGzDig4mGcR9+GwiW161E6PwEdwcq70wkW1qMMfTsZudoIx7yzzbY+isDkbEaWdlDsYzc6oF5ohQs3FrKOoX4P4m8+wqWKPVww4s65eVqxPR3+LLUREM4i7MS2TDqxlhdy6+FxX0rES2ulmiDGXlyQ6JrIiW41BGjU7ux+E8rbAWlyeyrTUk5uOqKAjn1NNoG2B9ByR2YXGl1agtDe7HvS1CcY6bEtlThy6kfbgokuIyXJLI2slNm6NUKooyfh2agCOIxK58t4XzbapuYaNw/BC+hj9gQSLb3oZRlTmLnIQKngjBb7hXqlesrYuQ2UjC2RZOxlA1eVoI0ztxZQckxDEpmsdeiobsn9UXjyASsX4xft6gvC9Xjl4cqYtDhbk9isBOUaSyOBjvuaM2gNQtnxPZi6GG31OHTG+VUj8Fn44duqdFGd8MSQGpdjB6omsS2RG717APSGRb8CX8robM5FBThFx5cmTnjR2SqMzZ7AvAIH6LSxt94W3a0CSyJyMvLK2qh8YhDSc/M+bYaKjj6xRvwrEN7h2IxHtYzmqLiENkLsJtYWw/PlEa6kMqCsi2To9V1GRTG8hCe3ADLmwVzgupholsay69HH+PD0Ez8a8Q6XRRYoijOa3mWjmS5Lfwq1b6mjbkT4ls34D09hJ/ie+Ll1V9AujUyeGdeGP8u4zn8AvcUmZDo+/qtShMxCFBLsull8VX31n4cKdEouk6P+zYFL74MzxY9P+gVNCVXBmVboq9iezxDp4/M5Lvigj16xsIFy3xP2jDDgQA0nqwAAAAAElFTkSuQmCC"

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    favicon_image = base64.b64decode(FAVICON_BASE64)
    return Response(content=favicon_image, media_type='image/x-icon')

PORT = 8000
if os.getenv("PORT"):
    PORT = int(str(os.getenv("PORT")))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
