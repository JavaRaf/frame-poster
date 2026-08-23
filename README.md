# Frame Poster

This project posts frames from an episode repository to Facebook with optional subtitle comments and random crop follow-up posts.

## Configuration

- `config.yml` contains the app settings, message templates and Facebook API version.
- Progress is persisted back into `config.yml` (`progress:` section) after each post.

## Running locally

Use the included virtual environment Python:

```bash
./.venv/Scripts/python.exe main.py --help
```

Example:

```bash
./.venv/Scripts/python.exe main.py --fb-token "$FB_TOKEN"
```

## Facebook token

- `FB_TOKEN` can be provided via environment variable (or a `.env` file).
- `--fb-token` overrides the environment value for the current run.

## Docker

Build the image:

```bash
docker build -t frame-poster .
```

Run it with a mounted config file and token:

```bash
docker run --rm \
  -v "$PWD/config.yml:/app/config.yml" \
  -e FB_TOKEN="<your_token>" \
  frame-poster
```
