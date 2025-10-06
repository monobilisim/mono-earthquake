import sql from '$lib/db';
import type { EarthquakeData } from './afad';

const KOERI_URL = 'http://www.koeri.boun.edu.tr/scripts/lst1.asp';

export class KoeriParser {
	async fetch_data(): Promise<string> {
		const headers = {
			'User-Agent':
				'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
			Accept: 'text/html,application/xhtml+xml,application/xml',
			'Accept-Language': 'en-US,en;q=0.9',
			'Accept-Encoding': 'gzip, deflate, br',
			Connection: 'keep-alive',
			'Upgrade-Insecure-Requests': '1',
			'Cache-Control': 'max-age=0'
		};

		try {
			const response = await fetch(KOERI_URL, { headers });

      console.log("Fetching from ", KOERI_URL);

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}
			return await response.text();
		} catch (e) {
			throw new Error(
				`Failed to fetch data from ${KOERI_URL}: ${e instanceof Error ? e.message : String(e)}`
			);
		}
	}

	parse_data(raw_data: string): EarthquakeData[] {
		const preMatch = raw_data.match(/<pre>(.*?)<\/pre>/s);
		if (!preMatch) {
			throw new Error('Failed to extract <pre> tag containing earthquake data');
		}

		const preContent = preMatch[1];
		const tableMatch =
			preContent.match(
				/Tarih\s+Saat\s+Enlem.*?Çözüm Niteliği\s*\n-+\s+-+\s+(.*?)(?:\n\s*\n|\Z)/s
			) || preContent.match(/Tarih.*?-+\s+-+\s+(.*?)(?:\n\s*\n|\Z)/s);

		if (!tableMatch) {
			throw new Error('Failed to extract earthquake data table');
		}

		const tableData = tableMatch[1];
		const earthquakes: EarthquakeData[] = [];

		for (const line of tableData.trim().split('\n')) {
			const trimmed = line.trim();
			if (!trimmed || trimmed.includes('------') || trimmed.includes('Tarih')) continue;

			try {
				// Primary regex pattern
				const pattern =
					/(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(.*?)\s{2,}(\S.*?)$/;
				let match = trimmed.match(pattern);

				let year, month, day, time_str, lat, lon, depth, md, ml, mw, location, quality;

				if (match) {
					[, year, month, day, time_str, lat, lon, depth, md, ml, mw, location, quality] = match;
				} else {
					// Fallback pattern
					const pattern2 =
						/(\d{4})\.(\d{2})\.(\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(-\.-|\d+\.\d+)\s+(.*?)$/;
					match = trimmed.match(pattern2);
					if (!match) continue;

					[, year, month, day, time_str, lat, lon, depth, md, ml, mw, location] = match;
					// Try to split location and quality
					const parts = location.trim().split(/\s+/);
					if (parts.length >= 2 && ['İlksel', 'REVIZE'].includes(parts[parts.length - 1])) {
						quality = parts.pop()!;
						location = parts.join(' ');
					} else {
						quality = 'İlksel';
					}
				}

				// Fix Turkish characters (common encoding issue)
				const fixTurkish = (s: string) =>
					s
						.replace(/Ý/g, 'İ')
						.replace(/Ð/g, 'Ğ')
						.replace(/Þ/g, 'Ş')
						.replace(/ý/g, 'ı')
						.replace(/ð/g, 'ğ')
						.replace(/þ/g, 'ş');

				location = fixTurkish(location.trim());
				quality = fixTurkish(quality.trim());

				const isoDate = `${year}-${month}-${day}`;
				const timestamp = `${isoDate}T${time_str}Z`;

				const latVal = parseFloat(lat);
				const lonVal = parseFloat(lon);
				const depthVal = parseFloat(depth);

				const mdVal = md === '-.-' ? null : parseFloat(md);
				const mlVal = ml === '-.-' ? null : parseFloat(ml);
				const mwVal = mw === '-.-' ? null : parseFloat(mw);

				const magnitudes = [mdVal, mlVal, mwVal].filter((m): m is number => m !== null);
				const maxMagnitude = magnitudes.length > 0 ? Math.max(...magnitudes) : null;

				earthquakes.push({
					timestamp,
					date: isoDate,
					time: time_str,
					latitude: latVal,
					longitude: lonVal,
					depth: depthVal,
					md: mdVal,
					ml: mlVal,
					mw: mwVal,
					magnitude: maxMagnitude,
					location,
					quality
				});
			} catch (e) {
				console.error('Error parsing line:', line);
				console.error('Error details:', e);
				continue;
			}
		}

		return earthquakes;
	}

	async get_earthquakes(): Promise<EarthquakeData[]> {
		try {
			const raw = await this.fetch_data();
			return this.parse_data(raw);
		} catch (e) {
			console.error('Error fetching/parsing earthquake data:', e);
			// Optionally save debug file (Node.js only)
			if (typeof window === 'undefined') {
				try {
					const fs = await import('fs').then((m) => m.promises);
					await fs.writeFile('debug_response.html', raw, 'utf-8');
					console.log('Saved raw response to debug_response.html');
				} catch {}
			}
			return [];
		}
	}

	async saveToDatabase(earthquakes?: EarthquakeData[]): Promise<EarthquakeData[]> {
  try {
    const earthquakesToSave = earthquakes ?? (await this.get_earthquakes());
    if (earthquakesToSave.length === 0) {
      return [];
    }

    const newEarthquakes: EarthquakeData[] = [];

    for (const eq of earthquakesToSave) {
      try {
        // Parse timestamp to extract date parts
        const timestamp = new Date(eq.timestamp);
        const year = timestamp.getFullYear();
        const month = timestamp.getMonth() + 1; // getMonth() is 0-indexed
        const day = timestamp.getDate();

        // Calculate ISO week number (Monday-based)
        const firstDayOfYear = new Date(year, 0, 1);
        const pastDaysOfYear = (timestamp.getTime() - firstDayOfYear.getTime()) / 86400000;
        const week = Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);

        // Check if already exists
        const existing = await sql`SELECT 1 FROM earthquakes WHERE timestamp = ${eq.timestamp}`;
        if (existing.length > 0) {
          continue;
        }

        // Insert and get ID
        const result = await sql`
          INSERT INTO earthquakes (
            timestamp, date, time, latitude, longitude, depth,
            md, ml, mw, magnitude, location, quality,
            year, month, day, week
          ) VALUES (
            ${eq.timestamp},
            ${eq.date},
            ${eq.time},
            ${eq.latitude},
            ${eq.longitude},
            ${eq.depth},
            ${eq.md},
            ${eq.ml},
            ${eq.mw},
            ${eq.magnitude},
            ${eq.location},
            ${eq.quality},
            ${year},
            ${month},
            ${day},
            ${week}
          )
          RETURNING id
        `;

        // Attach the database ID to the object
        const insertedId = result[0]?.id;
        if (insertedId !== undefined) {
          (eq as any).id = insertedId; // or define `id` in Earthquake interface
          newEarthquakes.push(eq);
        }
      } catch (error) {
        console.warn(`Error inserting earthquake with timestamp ${eq.timestamp}:`, error);
        continue;
      }
    }

    if (newEarthquakes.length > 0) {
      console.log(`Inserted ${newEarthquakes.length} new KOERI earthquakes`);
    }

    return newEarthquakes;
  } catch (error) {
    console.error('Error saving KOERI earthquakes to database:', error);
    throw new Error(`Failed to save earthquakes: ${error instanceof Error ? error.message : String(error)}`);
  }
}

	async get_earthquake_for_date(date: string): Promise<EarthquakeData[]> {
		return sql<EarthquakeData[]>`
      SELECT * FROM earthquakes WHERE date = ${date} ORDER BY timestamp DESC
    `;
	}

	async get_earthquakes_for_week(year: number, week: number): Promise<EarthquakeData[]> {
		// SQLite strftime: %Y-%W gives ISO year-week
		return sql<EarthquakeData[]>`
      SELECT * FROM earthquakes
      WHERE strftime('%Y-%W', date) = ${`${year}-${String(week).padStart(2, '0')}`}
      ORDER BY timestamp DESC
    `;
	}

	async get_earthquakes_for_month(year: number, month: number): Promise<EarthquakeData[]> {
		const monthStr = String(month).padStart(2, '0');
		return sql<EarthquakeData[]>`
      SELECT * FROM earthquakes
      WHERE date LIKE ${`${year}-${monthStr}-%`}
      ORDER BY timestamp DESC
    `;
	}

	async get_latest_earthquakes(limit = 1000): Promise<EarthquakeData[]> {
		return sql<EarthquakeData[]>`
      SELECT * FROM earthquakes
      ORDER BY timestamp DESC
      LIMIT ${limit}
    `;
	}

	async search_earthquakes({
		min_magnitude,
		max_magnitude,
		start_date,
		end_date,
		location_keyword,
		limit = 100
	}: {
		min_magnitude?: number;
		max_magnitude?: number;
		start_date?: string;
		end_date?: string;
		location_keyword?: string;
		limit?: number;
	}): Promise<EarthquakeData[]> {
		let query = sql`SELECT * FROM earthquakes WHERE 1=1`;
		const params: any[] = [];

		if (min_magnitude !== undefined) {
			query = sql`${query} AND magnitude >= ${min_magnitude}`;
		}
		if (max_magnitude !== undefined) {
			query = sql`${query} AND magnitude <= ${max_magnitude}`;
		}
		if (start_date) {
			query = sql`${query} AND date >= ${start_date}`;
		}
		if (end_date) {
			query = sql`${query} AND date <= ${end_date}`;
		}
		if (location_keyword) {
			query = sql`${query} AND location LIKE ${`%${location_keyword}%`}`;
		}

		query = sql`${query} ORDER BY timestamp DESC LIMIT ${limit}`;
		return query;
	}

	async get_database_stats(): Promise<Record<string, any>> {
		const [total, maxMag, recent] = await Promise.all([
			sql`SELECT COUNT(*) as total FROM earthquakes`,
			sql`SELECT MAX(magnitude) as max_magnitude FROM earthquakes`,
			sql`SELECT MAX(date) as latest_date FROM earthquakes`
		]);
		return {
			total_earthquakes: total[0]?.total ?? 0,
			max_magnitude: maxMag[0]?.max_magnitude ?? null,
			latest_date: recent[0]?.latest_date ?? null
		};
	}
}

// Example usage (in a SvelteKit endpoint or script)
if (import.meta.main) {
	const parser = new KoeriParser();
	const earthquakes = await parser.get_earthquakes();
	console.log(`Found ${earthquakes.length} earthquakes`);
	const inserted = await parser.saveToDatabase(earthquakes);
	console.log(`Inserted ${inserted} new records`);
}
