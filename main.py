from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, PlainTextResponse
import base64
from starlette.responses import FileResponse
import uvicorn
import asyncio
import logging
import os
import secrets
from datetime import datetime
import calendar
from parser import KoeriParser
from typing import Optional
from load_dotenv import load_dotenv
from webhooks import discord, zulip, whatsapp, generic
from polls_processor import process_whatsapp_webhook, get_template_statistics, is_polls_related_webhook
from polls import send_wa_template
from fastapi.staticfiles import StaticFiles
from database import EarthquakeDatabase

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
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        if new_records > 0:
            latest_earthquakes = parser.get_latest_earthquakes(new_records)

            earthquake_data = {
                "count": len(latest_earthquakes),
                "data": latest_earthquakes
            }

            await send_notifications_to_webhooks(earthquake_data)

            db = None
            try:
                db = EarthquakeDatabase()

                polls = db.get_polls()

                for poll in polls:
                    poll_name = poll["name"]
                    poll_type = poll["type"]

                    if poll_type == "whatsapp":
                        logger.info(f"Sending WhatsApp notification for poll: {poll_name}")
                        send_wa_template(poll_name, earthquake_data)

            except Exception as e:
                logger.error(f"Error sending notifications for polls: {str(e)}")
            finally:
                if db:
                    db.close()

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

async def send_notifications_to_webhooks(earthquake_data):
    """
    Send notifications to all registered webhooks.
    Each webhook receives the same earthquake record at roughly the same time,
    with a 3-second delay between sending different records.
    """
    db = None
    try:
        db = EarthquakeDatabase()

        # Get all webhooks
        webhooks = db.get_webhooks()

        if not webhooks:
            logger.info("No webhooks registered to receive notifications")
            return

        # Extract earthquake records
        earthquakes = earthquake_data.get("data", [])
        if not earthquakes:
            logger.info("No earthquake data to send")
            return

        logger.info(f"Sending {len(earthquakes)} earthquake records to {len(webhooks)} webhooks")

        # Process each earthquake record
        for i, earthquake in enumerate(earthquakes):
            # Create a single-earthquake data package
            single_quake_data = {
                "count": 1,
                "data": [earthquake]
            }

            logger.info(f"Distributing earthquake record {i+1}/{len(earthquakes)} to all webhooks")

            # Create tasks for sending this earthquake record to all webhooks
            tasks = []

            # Prepare a task for each webhook
            for webhook in webhooks:
                webhook_type = webhook['type']
                webhook_url = webhook['url']
                webhook_name = webhook['name']

                # Create a task (but don't await it yet)
                task = send_to_single_webhook(
                    webhook_type=webhook_type,
                    webhook_url=webhook_url,
                    webhook_name=webhook_name,
                    webhook_id=webhook['id'],
                    earthquake_data=single_quake_data,
                    db=db
                )
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks)
                logger.info(f"Finished sending earthquake record {i+1} to all webhooks")

            if i < len(earthquakes) - 1:
                logger.info("Waiting 5 seconds before sending next record...")
                await asyncio.sleep(3)  # 5-second delay between records

    except Exception as e:
        logger.error(f"Error sending notifications to webhooks: {str(e)}")
    finally:
        if 'db' in locals():
            if db is not None:
                db.close()

async def send_to_single_webhook(webhook_type, webhook_url, webhook_name, webhook_id, earthquake_data, db):
    """Helper function to send a single earthquake to a single webhook."""
    try:
        logger.info(f"Sending earthquake to webhook '{webhook_name}' of type '{webhook_type}'")

        success = False
        if webhook_type == 'discord':
            success = discord(webhook_url, earthquake_data)
        elif webhook_type == 'zulip':
            success = zulip(webhook_url, earthquake_data)
        elif webhook_type == 'whatsapp':
            success = whatsapp(webhook_url, earthquake_data)
        elif webhook_type == 'generic':
            success = generic(webhook_url, earthquake_data)

        if success:
            # Update the last_sent_at timestamp
            db.update_webhook_last_sent(webhook_id)
            logger.info(f"Successfully sent earthquake data to '{webhook_name}'")
        else:
            logger.warning(f"Failed to send earthquake data to '{webhook_name}'")

        return success
    except Exception as e:
        logger.error(f"Error sending to webhook '{webhook_name}': {str(e)}")
        return False

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

@app.get("/wa-callback", tags=["Webhooks"])
async def wa_callbackGet(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == str(os.getenv("WA_VERIFY_TOKEN")):
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse(content="Forbidden", status_code=403)

@app.post("/wa-callback", tags=["Webhooks"])
async def wa_callbackPost(request: Request):
    data = await request.json()

    logger.info("Received WhatsApp callback")
    logger.info(f"Request body: {data}")

    value = data["entry"][0]["changes"][0]["value"]

    is_read = False
    message = None
    id = None

    if "statuses" in value:
        id = value["statuses"][0].get("id")
        is_read = value["statuses"][0].get("status") == "read"

    if "messages" in value:
        id = value["messages"][0]["context"].get("id")
        message = value["messages"][0]["button"].get("text")

    db = None
    try:
        db = EarthquakeDatabase()

        if is_read is True and message is None:
            db.update_wa_message(id, True, None)

        if message is not None:
            db.update_wa_message(id, True, message)

        db.clear_old_wa_messages()

    except Exception as e:
        logger.error(f"Error updating WhatsApp message status in database: {str(e)}")

    finally:
        if db in locals():
            if db is not None:
                db.close()

    return Response(status_code=200)

@app.post("/wa_message_stats", tags=["Messages"])
async def wa_message_stats(request: Request):
    body = await request.json()
    logger.info(body)

    username = None
    password = None
    session = None
    if body.get("username") is not None:
        username = body.get("username")
    if body.get("password") is not None:
        password = body.get("password")
    if body.get("session") is not None:
        session = body.get("session")

    if not session and (not username or not password):
        return Response(status_code=400, content="Username and password required")

    db = None
    try:
        db = EarthquakeDatabase()

        session_token = None
        if not session:
            user_id = db.authenticate_user(username, password)
            if user_id is None:
                return JSONResponse(status_code=401, content={"message": "Invalid username or password"})
            session_token = secrets.token_urlsafe(32)
            db.create_session(user_id, session_token)

        if session:
            if db.check_session(session) is not True:
                return JSONResponse(status_code=403, content={"message": "Invalid session token"})

        rows = db.get_wa_messages()

        if not rows:
            return JSONResponse(status_code=404, content={"message": "No WhatsApp webhook statistics found"})

        if session:
            return JSONResponse(
                status_code=200,
                content={
                    "count": len(rows),
                    "data": rows,
                }
            )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "count": len(rows),
                    "data": rows,
                    "session_token": session_token
                }
            )

    except Exception as e:
        logger.error(f"Error in wa_message_stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": f"Error fetching WhatsApp webhook statistics: {str(e)}"}
        )

    finally:
        if db:
            db.close()

app.mount("/static", StaticFiles(directory="ui/dist", html=True), name="static")
app.mount("/assets", StaticFiles(directory="ui/dist/assets"), name="assets")

@app.get("/", tags=["Ui"])
async def get_ui():
    return FileResponse("ui/dist/index.html")

@app.get("/assets/{asset}", tags=["Ui"])
async def get_asset(asset: str):
    return FileResponse(f"ui/dist/assets/{asset}")

# @app.get("/", tags=["Info"])
# async def root():
#     """Root endpoint providing API information"""
#     return {
#         "name": "KOERI Earthquake Data API",
#         "version": "1.2.0",
#         "description": "API for accessing earthquake data from Kandilli Observatory and Earthquake Research Institute",
#         "database": "SQLite",
#         "endpoints": {
#             "GET /docs": "Swagger based documentation page for API usage",
#             "GET /stats": "Get statistics about the earthquake database",
#             "GET /earthquakes/latest": "Get the latest earthquake data",
#             "GET /earthquakes/day/{date}": "Get earthquake data for a specific date",
#             "GET /earthquakes/week/{year}/{week}": "Get earthquake data for a specific week",
#             "GET /earthquakes/month/{year}/{month}": "Get earthquake data for a specific month",
#             "GET /earthquakes/search": "Search earthquake data based on various criteria"
#         }
#     }

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

FAVICON_BASE64 = "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"

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    favicon_image = base64.b64decode(FAVICON_BASE64)
    return Response(content=favicon_image, media_type='image/x-icon')

PORT = 8000
if os.getenv("PORT"):
    PORT = int(str(os.getenv("PORT")))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
