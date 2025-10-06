import sql from '$lib/db';

export interface EarthquakeData {
	timestamp: string;
	date: string;
	time: string;
	latitude: number;
	longitude: number;
	depth: number;
	md?: number | null;
	ml?: number | null;
	mw?: number | null;
	magnitude?: number | null;
	location: string;
	quality: string;
}

export interface DatabaseStats {
	totalEarthquakes: number;
	latestTimestamp?: string;
	averageMagnitude?: number;
	maxMagnitude?: number;
	minMagnitude?: number;
	averageDepth?: number;
	maxDepth?: number;
	minDepth?: number;
}

export interface SearchCriteria {
	minMagnitude?: number;
	maxMagnitude?: number;
	startDate?: string;
	endDate?: string;
	locationKeyword?: string;
	limit?: number;
}

interface AfadEarthquake {
	eventID: string;
	magnitude: string;
	longitude: string;
	latitude: string;
	depth: string;
	date: string; // Changed from eventDate
	location: string;
	type: string; // Changed from magType
	rms?: string;
	country?: string;
	province?: string;
	district?: string;
	neighborhood?: string;
	isEventUpdate?: boolean;
	lastUpdateDate?: string | null;
}

// Constants
const AFAD_URL = 'https://deprem.afad.gov.tr/apiv2/event/filter';

export class KoeriParser {
	async fetchData(
		options: {
			startDate?: string;
			endDate?: string;
			minMagnitude?: number;
			maxMagnitude?: number;
			limit?: number;
		} = {}
	): Promise<string> {
		try {
			// Last 1 hour by default
			const endDate = options.endDate || new Date().toISOString().split('T')[0];
			const startDate =
				options.startDate || new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString().split('T')[0];

			const minimumPollThresholds = await sql`SELECT MIN(threshold) as threshold FROM polls`;

			const minimumPollThreshold = minimumPollThresholds[0]?.threshold || 5;

			const params = new URLSearchParams({
				start: `${startDate} 00:00:00`,
				end: `${endDate} 23:59:59`,
				format: 'json',
				orderby: 'timedesc',
				limit: (options.limit || 500).toString(),
				minmag: (minimumPollThreshold - 0.1).toString()
			});

			if (options.minMagnitude !== undefined) {
				params.append('minmag', options.minMagnitude.toString());
			}

			if (options.maxMagnitude !== undefined) {
				params.append('maxmag', options.maxMagnitude.toString());
			}

			const url = `${AFAD_URL}?${params.toString()}`;
			console.log(`Fetching from ${url}`);

			const headers = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
				Accept: 'application/json',
				'Accept-Language': 'en-US,en;q=0.9'
			};

			const response = await fetch(url, {
				method: 'GET',
				headers,
				signal: AbortSignal.timeout(30000)
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.text();
		} catch (error) {
			if (error instanceof Error) {
				throw new Error(`Failed to fetch data from AFAD API: ${error.message}`);
			}
			throw new Error(`Failed to fetch data from AFAD API: Unknown error`);
		}
	}

	parseData(rawData: string): EarthquakeData[] {
		try {
			const jsonData = JSON.parse(rawData);

			let earthquakeArray: AfadEarthquake[] = [];

			if (Array.isArray(jsonData)) {
				earthquakeArray = jsonData;
			} else if (jsonData.result && Array.isArray(jsonData.result)) {
				earthquakeArray = jsonData.result;
			} else if (jsonData.data && Array.isArray(jsonData.data)) {
				earthquakeArray = jsonData.data;
			} else {
				console.warn('Unexpected API response format:', jsonData);
				return [];
			}

			const earthquakes: EarthquakeData[] = [];

			for (const afadEarthquake of earthquakeArray) {
				try {
					if (!afadEarthquake.date) {
						console.warn('Missing date in earthquake data:', afadEarthquake);
						continue;
					}

					const eventDateTimeUTC = new Date(afadEarthquake.date);
					const eventDateTime = new Date(eventDateTimeUTC.getTime() + 3 * 60 * 60 * 1000); // Convert UTC to GMT+3

					if (isNaN(eventDateTime.getTime())) {
						console.warn('Invalid date format:', afadEarthquake.date);
						continue;
					}

					const timestamp = eventDateTime.toISOString();

					const date = eventDateTime.toISOString().split('T')[0];
					const time = eventDateTime.toTimeString().split(' ')[0];

					const magnitude = parseFloat(afadEarthquake.magnitude) || 0;
					const latitude = parseFloat(afadEarthquake.latitude) || 0;
					const longitude = parseFloat(afadEarthquake.longitude) || 0;
					const depth = parseFloat(afadEarthquake.depth) || 0;

					const earthquake: EarthquakeData = {
						timestamp,
						date,
						time,
						latitude,
						longitude,
						depth,
						md: null,
						ml: afadEarthquake.type === 'ML' ? magnitude : null,
						mw: afadEarthquake.type === 'Mw' ? magnitude : null,
						magnitude,
						location: afadEarthquake.location || 'Unknown',
						quality: 'AFAD' // It was for KOERI originally but AFAD does not provide quality info so...
					};

					earthquakes.push(earthquake);
				} catch (error) {
					console.error(`Error parsing individual earthquake:`, afadEarthquake, error);
					continue;
				}
			}

			return earthquakes;
		} catch (error) {
			console.error('Error parsing JSON data:', error);
			throw new Error('Failed to parse earthquake data from AFAD API');
		}
	}

	async getEarthquakes(
		options: {
			startDate?: string;
			endDate?: string;
			minMagnitude?: number;
			maxMagnitude?: number;
			limit?: number;
		} = {}
	): Promise<EarthquakeData[]> {
		try {
			const rawData = await this.fetchData(options);
			return this.parseData(rawData);
		} catch (error) {
			console.error(`Error getting earthquake data: ${error}`);
			return [];
		}
	}

	async saveToDatabase(earthquakes?: EarthquakeData[]): Promise<EarthquakeData[]> {
		try {
			const earthquakesToSave = earthquakes || (await this.getEarthquakes());

			if (earthquakesToSave.length === 0) {
				return [];
			}

			const newEarthquakes: EarthquakeData[] = [];

			for (const earthquake of earthquakesToSave) {
				try {
					const timestamp = new Date(earthquake.timestamp);
					const year = timestamp.getFullYear();
					const month = timestamp.getMonth() + 1;
					const day = timestamp.getDate();

					const firstDayOfYear = new Date(year, 0, 1);
					const pastDaysOfYear = (timestamp.getTime() - firstDayOfYear.getTime()) / 86400000;
					const week = Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);

					// Check if earthquake already exists
					const existing =
						await sql`SELECT 1 FROM earthquakes WHERE timestamp = ${earthquake.timestamp}`;

					if (existing.length > 0) {
						continue;
					}

					const insertedRow = await sql`
						INSERT INTO earthquakes (
							timestamp, date, time, latitude, longitude, depth, md, ml, mw, magnitude, location, quality, year, month, day, week
						) VALUES (
							${earthquake.timestamp},
							${earthquake.date},
							${earthquake.time},
							${earthquake.latitude},
							${earthquake.longitude},
							${earthquake.depth},
							${earthquake.md},
							${earthquake.ml},
							${earthquake.mw},
							${earthquake.magnitude},
							${earthquake.location},
							${earthquake.quality},
							${year},
							${month},
							${day},
							${week}
						) RETURNING id
					`;

					earthquake['id'] = insertedRow[0].id;

					newEarthquakes.push(earthquake);
				} catch (error) {
					console.warn(`Error inserting earthquake:`, error);
					continue;
				}
			}

			if (newEarthquakes.length > 0) {
				console.log(`Inserted ${newEarthquakes.length} new earthquakes`);
			}

			return newEarthquakes;
		} catch (error) {
			console.error(`Error saving to database:`, error);
			throw new Error(`Error saving to database: ${error}`);
		}
	}

	async searchEarthquakes(criteria: SearchCriteria): Promise<EarthquakeData[]> {
		const minMag = criteria.minMagnitude ?? -10;
		const maxMag = criteria.maxMagnitude ?? 15;
		const startDate = criteria.startDate ?? '1900-01-01';
		const endDate = criteria.endDate ?? '2100-12-31';
		const locationPattern = criteria.locationKeyword ? `%${criteria.locationKeyword}%` : '%';
		const limit = criteria.limit ?? 1000;

		const rows = await sql`
			SELECT timestamp, date, time, latitude, longitude, depth, md, ml, mw, magnitude, location, quality
			FROM earthquakes
			WHERE (magnitude >= ${minMag} OR magnitude IS NULL)
				AND (magnitude <= ${maxMag} OR magnitude IS NULL)
				AND date >= ${startDate}
				AND date <= ${endDate}
				AND location LIKE ${locationPattern}
			ORDER BY timestamp DESC
			LIMIT ${limit}
		`;

		return rows.map(this.convertRowToEarthquake);
	}

	async getDatabaseStats(): Promise<DatabaseStats> {
		const countResult = await sql`SELECT COUNT(*) as count FROM earthquakes`;
		const totalEarthquakes = countResult[0]?.count || 0;

		if (totalEarthquakes === 0) {
			return { totalEarthquakes: 0 };
		}

		const statsResult = await sql`
			SELECT
				MAX(timestamp) as latestTimestamp,
				AVG(magnitude) as averageMagnitude,
				MAX(magnitude) as maxMagnitude,
				MIN(magnitude) as minMagnitude,
				AVG(depth) as averageDepth,
				MAX(depth) as maxDepth,
				MIN(depth) as minDepth
			FROM earthquakes
			WHERE magnitude IS NOT NULL
		`;

		const stats = statsResult[0];

		return {
			totalEarthquakes,
			latestTimestamp: stats?.latestTimestamp || undefined,
			averageMagnitude: stats?.averageMagnitude || undefined,
			maxMagnitude: stats?.maxMagnitude || undefined,
			minMagnitude: stats?.minMagnitude || undefined,
			averageDepth: stats?.averageDepth || undefined,
			maxDepth: stats?.maxDepth || undefined,
			minDepth: stats?.minDepth || undefined
		};
	}

	private convertRowToEarthquake(row: any): EarthquakeData {
		return {
			timestamp: row.timestamp,
			date: row.date,
			time: row.time,
			latitude: row.latitude,
			longitude: row.longitude,
			depth: row.depth,
			md: row.md,
			ml: row.ml,
			mw: row.mw,
			magnitude: row.magnitude,
			location: row.location,
			quality: row.quality
		};
	}
}
