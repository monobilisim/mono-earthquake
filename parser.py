import requests
import re
import os
from typing import List, Dict, Any, Optional
from database import EarthquakeDatabase

# URL of the KOERI earthquake data
KOERI_URL = "http://www.koeri.boun.edu.tr/scripts/lst1.asp"

given_db_path = os.getenv("DB_PATH");

class KoeriParser:
    """
    Parser for KOERI earthquake data from Bogazici University.
    Fetches and parses earthquake data, saving it in SQLite database.
    """

    def __init__(self, db_path: str = "data/earthquakes.db"):
        """
        Initialize the parser with a database file path.

        Args:
            db_path: Path to the SQLite database file
        """

        self.db = EarthquakeDatabase(db_path)

    def fetch_data(self) -> str:
        """
        Fetch earthquake data from KOERI website.

        Returns:
            Raw text data from the KOERI website
        """
        try:
            # Use headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            response = requests.get(KOERI_URL, timeout=30, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to fetch data from {KOERI_URL}: {e}")

    def parse_data(self, raw_data: str) -> List[Dict[str, Any]]:
        """
        Parse raw text data into structured format.

        Args:
            raw_data: Raw text data from KOERI website

        Returns:
            List of dictionaries containing parsed earthquake data
        """
        # Try to extract the tabular data part
        # First look for the pre tag which contains the table
        pre_match = re.search(r'<pre>(.*?)</pre>', raw_data, re.DOTALL)
        if not pre_match:
            raise ValueError("Failed to extract pre tag containing earthquake data")

        pre_content = pre_match.group(1)

        # Look for the header and dashed line pattern that indicates the start of earthquake data
        table_match = re.search(r'Tarih\s+Saat\s+Enlem.*?Çözüm Niteliği\s*\n-+\s+-+\s+(.*?)(?:\n\s*\n|\Z)', pre_content, re.DOTALL)

        if not table_match:
            # Try alternative pattern if the first one fails
            table_match = re.search(r'Tarih.*?-+\s+-+\s+(.*?)(?:\n\s*\n|\Z)', pre_content, re.DOTALL)

            if not table_match:
                raise ValueError("Failed to extract earthquake data table from the response")

        table_data = table_match.group(1)
        earthquakes = []

        # Process each line in the table
        for line in table_data.strip().split('\n'):
            line = line.strip()
            if not line or "------" in line or "Tarih" in line:
                continue

            try:
                # Extract fields using regular expression for the current format
                # Convert YYYY.MM.DD to YYYY-MM-DD
                # In the current format, the location is followed by quality with multiple spaces in between
                # Sample: 2025.05.13 09:05:56  36.9173   27.6803        8.9      -.-  1.4  -.-   GOKOVA KORFEZI (EGE DENIZI)                       Ýlksel
                pattern = r'(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(.*?)\s{2,}(\S.*?)$'
                match = re.match(pattern, line)

                if not match:
                    # Try an alternative pattern with more flexible whitespace
                    pattern2 = r'(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(.*?)$'
                    match = re.match(pattern2, line)

                    if match:
                        # Extract location and quality from the combined field
                        year, month, day, time_str, lat, lon, depth, md, ml, mw, location_quality = match.groups()
                        date_str = f"{year}.{month}.{day}"

                        # Try to separate location and quality
                        parts = location_quality.strip().rsplit(maxsplit=1)
                        if len(parts) >= 2 and parts[-1] in ["İlksel", "REVIZE"]:
                            location = parts[0].strip()
                            quality = parts[-1].strip()
                        else:
                            location = location_quality.strip()
                            quality = "İlksel"  # Default value
                    else:
                        continue
                else:
                    year, month, day, time_str, lat, lon, depth, md, ml, mw, location, quality = match.groups()
                    date_str = f"{year}.{month}.{day}"

                # Convert date from YYYY.MM.DD to YYYY-MM-DD format for ISO compatibility
                date_parts = date_str.split('.')
                iso_date = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"

                # Create timestamp
                timestamp = f"{iso_date}T{time_str}Z"

                # Clean up location and quality fields (handle encoding issues)
                location = location.strip().replace('Ý', 'İ').replace('Ð', 'Ğ').replace('Þ', 'Ş')
                quality = quality.strip().replace('Ý', 'İ').replace('Ð', 'Ğ').replace('Þ', 'Ş')

                # Parse numeric values
                lat_val = float(lat)
                lon_val = float(lon)
                depth_val = float(depth)

                # Handle magnitude values
                md_val = None if md == "-.-" else float(md)
                ml_val = None if ml == "-.-" else float(ml)
                mw_val = None if mw == "-.-" else float(mw)

                # Determine the highest magnitude
                magnitudes = [m for m in [md_val, ml_val, mw_val] if m is not None]
                max_magnitude = max(magnitudes) if magnitudes else None

                earthquake = {
                    "timestamp": timestamp,
                    "date": iso_date,
                    "time": time_str,
                    "latitude": lat_val,
                    "longitude": lon_val,
                    "depth": depth_val,
                    "md": md_val,
                    "ml": ml_val,
                    "mw": mw_val,
                    "magnitude": max_magnitude,
                    "location": location.strip(),
                    "quality": quality.strip(),
                }

                earthquakes.append(earthquake)
            except Exception as e:
                print(f"Error parsing line: {line}")
                print(f"Error details: {e}")
                continue

        return earthquakes

    def get_earthquakes(self) -> List[Dict[str, Any]]:
        """
        Fetch and parse earthquake data.

        Returns:
            List of parsed earthquake records
        """
        raw_data = self.fetch_data()
        try:
            return self.parse_data(raw_data)
        except Exception as e:
            print(f"Error parsing earthquake data: {str(e)}")
            # If parsing fails, try to save the raw response for debugging
            try:
                debug_path = "debug_response.html"
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(raw_data)
                print(f"Saved raw response to {debug_path}")
            except:
                pass
            # Return empty list if parsing fails
            return []

    def save_to_database(self, earthquakes: Optional[List[Dict[str, Any]]] = None) -> int:
        """
        Save earthquake data to SQLite database.

        Args:
            earthquakes: Optional list of earthquake records. If None, fetches new data.

        Returns:
            Number of records inserted
        """
        if earthquakes is None:
            earthquakes = self.get_earthquakes()

        return self.db.insert_earthquakes(earthquakes)

    def get_earthquake_for_date(self, date: str) -> List[Dict[str, Any]]:
        """
        Get earthquake data for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            List of earthquake records for the specified date
        """
        return self.db.get_earthquakes_by_date(date)

    def get_earthquakes_for_week(self, year: int, week: int) -> List[Dict[str, Any]]:
        """
        Get earthquake data for a specific week.

        Args:
            year: Year as integer
            week: Week number as integer

        Returns:
            List of earthquake records for the specified week
        """
        return self.db.get_earthquakes_by_week(year, week)

    def get_earthquakes_for_month(self, year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get earthquake data for a specific month.

        Args:
            year: Year as integer
            month: Month as integer

        Returns:
            List of earthquake records for the specified month
        """
        return self.db.get_earthquakes_by_month(year, month)

    def get_latest_earthquakes(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get the latest earthquake records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of the latest earthquake records
        """
        return self.db.get_latest_earthquakes(limit)

    def search_earthquakes(self,
                          min_magnitude: Optional[float] = None,
                          max_magnitude: Optional[float] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          location_keyword: Optional[str] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for earthquakes based on various criteria.

        Args:
            min_magnitude: Minimum magnitude
            max_magnitude: Maximum magnitude
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            location_keyword: Keyword to search in location field
            limit: Maximum number of records to return

        Returns:
            List of matching earthquake records
        """
        return self.db.search_earthquakes(
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            start_date=start_date,
            end_date=end_date,
            location_keyword=location_keyword,
            limit=limit
        )

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the database.

        Returns:
            Dictionary containing statistics about the earthquake data
        """
        return self.db.get_summary_statistics()

    def close(self):
        """Close the database connection."""
        self.db.close()

    def __del__(self):
        """Destructor to ensure database connection is closed."""
        self.close()

if __name__ == "__main__":
    # Example usage
    parser = KoeriParser()
    earthquakes = parser.get_earthquakes()
    print(f"Found {len(earthquakes)} earthquakes")
    records = parser.save_to_database(earthquakes)
    print(f"Inserted {records} new records into database")
    parser.close()
