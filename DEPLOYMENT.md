# Deployment Guide

This document outlines the common deployment patterns for the Bible API, including running as a service on Windows and running inside Docker.

## ✅ Docker (Recommended for Portable Deployments)

The repository includes a `docker-compose.yml`, along with `Dockerfile.dev` and `Dockerfile.prod`.

> Deployment artifacts have been consolidated under `deploy/`. See `deploy/windows-service/` for Windows service assets.

### Run locally (development)

```powershell
docker compose up --build
```

The service will start with the embedded `bible_v2.db` file mounted into the container.

### Build & run (production)

```powershell
docker build -f Dockerfile.prod -t bible-api:prod .
docker run -p 9091:9091 bible-api:prod
```

## ✅ Windows Service (WinSW)

Deployment assets for Windows service hosting are consolidated under `deploy/windows-service/`.

- `deploy/windows-service/WINDOWS_SERVICE.md` contains setup instructions and example service `xml`.
- `deploy/windows-service/start_bible_server.bat` can be used as a standalone launcher.

### Summary

1. Download/produce `bible_v2.db` and place it in the same folder as the server binary.
2. Use `WinSW` to wrap `bible_server.exe` as a service (configured via `bible_server_task.xml`).
3. Start the service via `sc start bible_server` or via Task Scheduler.

## ✅ CI / Quality

Continuous testing is configured via GitHub Actions in `.github/workflows/python-ci.yml`.

- Runs on pushes and pull requests to `main`
- Executes `python -m pytest -q` to ensure tests pass

---

If you require a different deployment target (e.g., Azure App Service, GKE, AWS ECS), let me know and I can add a tailored guide.
