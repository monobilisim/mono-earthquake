# KOERI Earthquake Data API

This API fetches, parses, and serves earthquake data from the Kandilli Observatory and Earthquake Research Institute (KOERI) of Boğaziçi University.

## Features

- Search from stored earthquake data
- Easily fetch data based on date and time

## Installation

1. Clone this repository:

```bash
git clone https://github.com/monobilisim/mono-earthquake.git
cd mono-earthquake
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run

```bash
python3 main.py
```

## Alternative Installation

1. Install `docker` or `podman` with `podman-docker`

https://docs.docker.com/engine/install/debian

```bash
apt install podman podman-docker
```

2. Clone this repository

```bash
git clone https://github.com/monobilisim/mono-earthquake.git
cd mono-earthquake
```

3. Run

```bash
docker compose up -d
```

## Usage

### CLI

```console
python3 manage-webhooks.py help
```

### Running the API

By default, the API binds itself to `http://0.0.0.0:8000`.

### API Documentation

Once the API is running, you can access the Swagger documentation at `http://127.0.0.1:8000/docs`.

### Adding webhooks

```console
python3 manage-webhooks.py <type> <url> <name>
```

#### Currently supported webhook providers

Discord,
Zulip (slack_incoming),
Generic json```{count: n, data:[{},{}] }```

Each data object structured like
```json
{
  "timestamp": "2023-11-15T08:18:34Z",
  "date": "2023-11-15",
  "time": "08:18:34",
  "latitude": 39.2558,
  "longitude": 28.9703,
  "depth": 5.4,
  "md": null,
  "ml": 2.3,
  "mw": null,
  "magnitude": 2.3,
  "location": "YEMISLI-SIMAV (KUTAHYA)",
  "quality": "İlksel"
}
```

## License

This project is licensed under the GPL3 License - see the LICENSE file for details.
