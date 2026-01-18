# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Containerized microservices for the Fako K3s cluster. Each app is independently deployed via GitHub Actions → DockerHub → K8s GitOps (manifests live in `fako-cluster` repo).

## Applications

| App | Purpose | Type | Namespace |
|-----|---------|------|-----------|
| `audio-compressor` | SFTP → FFmpeg compression → PVC | K8s CronJob | `audio-processing` |
| `audio-transcriber` | Whisper API batch transcription | K8s Job | `audio-processing` |
| `oura-collector` | Oura Ring API → PostgreSQL + daily reports | K8s Deployment | `oura` |
| `oura-dashboard` | Streamlit health visualization | K8s Deployment | `oura` |
| `oura-agent` | Discord health bot (Claude + LangGraph) | K8s Deployment | `oura-agent` |
| `katikaa-health-monitor` | Financial/health monitoring | K8s Deployment | `katikaa` |

## Common Commands

### Local Development
```bash
# Run an app locally (set env vars first)
cd apps/audio-compressor
python -m src.main

# oura-agent: single poll cycle for testing
cd apps/oura-agent
RUN_ONCE=true python -m src.main

# Build Docker image locally
docker build -t audio-compressor:dev apps/audio-compressor/

# Test Docker image
docker run -it --rm \
  -e SFTP_HOST=... \
  -e SFTP_USERNAME=... \
  -v /tmp/data:/data \
  audio-compressor:dev

# Syntax validation (useful for oura-agent)
python -m py_compile src/main.py src/config.py
```

### Deployment
```bash
# Push to main triggers GitHub Actions build
git add apps/audio-compressor/
git commit -m "fix(audio-compressor): description"
git push origin main

# Watch deployment (K8s manifests in fako-cluster repo)
kubectl logs -f job/audio-compressor -n audio-processing
kubectl logs -f deployment/oura-collector -n oura
kubectl logs -f deployment/oura-agent -n oura-agent
```

### Debugging
```bash
# View job logs
kubectl logs -n audio-processing -l job-name=audio-compressor-xxxxx

# Check manifest stats
kubectl exec -it <pod> -- cat /data/compressed/manifest.json

# Storage usage
kubectl exec -it <pod> -- du -sh /data/compressed

# oura-collector: check freshness status
kubectl logs -n oura deployment/oura-collector | grep -i stale
```

## Architecture

### Audio Pipeline
```
SFTP Server (/audio/)
    ↓
audio-compressor (CronJob, 2 AM daily)
    ├── Downloads WAV files via SFTP (paramiko)
    ├── FFmpeg: 16kHz, mono, 32kbps MP3
    └── Output: /data/compressed (PVC)
         ↓
audio-transcriber (Job, manual trigger)
    ├── Scans PVC for audio files
    ├── Auto-chunks files >24MB
    ├── Calls Whisper API (OpenAI SDK format)
    └── Output: JSON/TXT/SRT/VTT transcriptions
```

### Health Data Pipeline
```
Oura Ring API
    ↓
oura-collector (Deployment, continuous)
    ├── Smart backfill from last collected date
    ├── 11 data types (sleep, activity, readiness, HR, etc.)
    ├── Stale data detection with Discord alerts
    ├── Daily/weekly health reports → Discord + Obsidian vault
    └── PostgreSQL storage (SQLAlchemy 2.0)
         ↓
    ┌────┴────┐
    ↓         ↓
oura-dashboard          oura-agent
(Streamlit, port 8501)  (Discord bot, polling)
    └ Plotly charts         ├── Multi-agent architecture (LangGraph)
                            ├── Supervisor routes to specialists:
                            │   SleepAnalyst, FitnessCoach,
                            │   MemoryKeeper, DataAuditor
                            └── pgvector episodic memory
```

## App Structure Pattern

Each app follows this structure:
```
apps/{app-name}/
├── src/
│   ├── main.py            # Entry point
│   ├── config.py          # Env var loader
│   └── ...                # App-specific modules
├── externalconnections/
│   └── fetch_*_secrets.py # AWS Secrets Manager wrapper
├── Dockerfile             # python:3.11-slim, non-root user
├── requirements.txt       # Pinned dependencies
└── README.md              # Config reference
```

**oura-agent** has additional structure for multi-agent architecture:
```
apps/oura-agent/
├── src/
│   ├── agents/            # Supervisor + specialist agents
│   │   ├── supervisor.py  # Routes queries to specialists
│   │   ├── sleep_analyst.py
│   │   ├── fitness_coach.py
│   │   ├── memory_keeper.py
│   │   └── data_auditor.py
│   └── tools/             # LangChain tools for Oura data
├── database/
│   ├── queries.py         # 55+ async SQLAlchemy queries
│   └── data_quality.py    # DataQualityValidator
├── memory/
│   ├── working.py         # LangGraph checkpointer
│   └── episodic.py        # pgvector semantic search
└── discord/
    └── client.py          # Discord API (fetch, send, react)
```

## Key Patterns

**Configuration**: All via environment variables (12-factor), no config files

**Secrets**: AWS Secrets Manager with env var fallback:
```python
# externalconnections/fetch_*_secrets.py
client = boto3.client("secretsmanager")
secret = client.get_secret_value(SecretId=secret_name)
```

**Exit Codes**:
- `0` = Success (all items processed)
- `1` = Partial failure (some items failed)
- `2` = Total failure (config error, connection failed)

**Manifest Tracking**: JSON files with processing stats for job monitoring

**Data Freshness** (oura-collector): StaleDataDetector checks table freshness and posts Discord alerts when data is stale (sleep/activity >2 days, VO2 Max >30 days)

**Daily Reports** (oura-collector): DailyHealthReporter generates summaries at configured hour, posting to Discord webhook and saving markdown to Obsidian vault

## CI/CD

GitHub Actions (`.github/workflows/{app}-build.yaml`):
1. Triggers on push to `main` when `apps/{app}/**` changes
2. Multi-arch build: `linux/amd64,linux/arm64` (QEMU)
3. Push to DockerHub: `lzetam/{app}:latest` and `:{sha}`
4. K8s pulls new image (GitOps via fako-cluster)

## Adding a New App

1. Create `apps/{app-name}/` with standard structure
2. Copy workflow from existing app, update paths/names
3. Add K8s manifests in `fako-cluster` repo
4. Configure secrets in AWS Secrets Manager

## App-Specific Notes

### oura-agent
See `apps/oura-agent/CLAUDE.md` for detailed multi-agent architecture, routing examples, and memory systems. Key points:
- Polling-based Discord integration (30s interval)
- Thread ID format: `oura-health-{user_id}-{channel_id}`
- Episodic memory uses 768-dim embeddings via Ollama nomic-embed-text
- All agents validate data freshness before responding
