# Frame Poster

This project posts frames from an episode repository to Facebook with optional subtitle comments and random crop follow-up posts.

## Configuration

- `configs.yml` contains the app settings and Facebook API version.
- `src/settings.py` centralizes project paths and environment loading.

## Running locally

Use the included virtual environment Python:

```bash
./.venv/Scripts/python.exe main.py --help
```

Example:

```bash
./.venv/Scripts/python.exe main.py \
  --config-file configs.yml \
  --fb-token "$FB_TOKEN" \
```

## Facebook token

- `FB_TOKEN` can be provided via environment variable.
- `--fb-token` overrides the environment value for the current run.

## Docker

Build the image:

```bash
docker build -t frame-poster .
```

Run it with a mounted config file and token:

```bash
docker run --rm \
  -v "$PWD/configs.yml:/app/configs.yml" \
  -e FB_TOKEN="<your_token>" \
  frame-poster
```

