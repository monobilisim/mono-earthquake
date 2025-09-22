# How to install and use

First copy .env.example to .env and fill in the required fields.

```bash
cp .env.example .env
```

Then install Docker and Docker Compose or Podman and Podman Compose with podman-docker compatibility layer.

Last step is to run the containers.

```bash
docker compose up -d
```

# How do i use it?

You need to create your account first. With this SQL query.

```sql
INSERT INTO users (name, phone_number, groups, roles) VALUES ('Your Name', 'Your Phone Number', 'admin or your company name', 'admin');
```

Then create the poll named "deprem" and choose the type with the following SQL query.
The lowest threshold in polls table will be used to fetch the data for earthquakes.

```sql
INSERT INTO polls (name, type, threshold) VALUES ('deprem', 'whatsapp', 5.0);
```

Make sure Meta Whatsapp webhook URL is configured to http://your-server-ip:8000/wa-callback without you can't login.

Open your browser and go to http://ipv4:8000
