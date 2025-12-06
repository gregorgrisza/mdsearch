# Simple search engine for MD documents

## Development

Requires docker.
Checkout sources.

1. Collect documents:
```bash
cd ${PROJECT_ROOT}
rm -fr docs/*
./collect_mds.sh <md_sources_directory>
```
2. Open project in dev container
3. Open Terminal and execute:
```bash
docker compose up --build
```
Couple seconds after you can attach debugger on port 5678. Configuration is already in `launch.json`

## Deployement

There is no deployment implemented, but you can simply comment "debugpy" from Dockerfile out,
docker compose will create setup closer to production

## Containers

DevContainer doesn't start services. Services are started by `docker compose up` in two containers.
One is Qdrant with exposed 6333 and second one is Server with webpage exposing 8000 (www) and 
5678 (python debuging)

### Server

Works on localhost:8000

### Qdrant

Works on localhost:6333

You can play with data on http://localhost:6333/dashboard
