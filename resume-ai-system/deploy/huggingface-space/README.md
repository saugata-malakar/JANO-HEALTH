---
title: HireSense API
emoji: 🎯
colorFrom: orange
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: AI résumé shortlisting & interview-question API
---

# HireSense API — Hugging Face Space

This Space hosts the FastAPI backend for [HireSense](https://github.com/saugata-malakar/JANO-HEALTH).

- Swagger UI: `<this-space-url>/docs`
- Demo evaluation: `<this-space-url>/api/demo/sample-evaluation`

## To deploy

1. Create a new Space at https://huggingface.co/new-space → SDK: **Docker**.
2. Clone the Space's git repo locally.
3. Copy this directory's `Dockerfile` and `README.md` to the Space root.
4. Also copy the `resume-ai-system/backend/` directory into the Space root (the Dockerfile expects it there, or adjust paths).
5. Push. HF builds the image and exposes the API at `https://<your-username>-<space-name>.hf.space`.
6. To enable LLM features, add `ANTHROPIC_API_KEY` as a Space secret in Settings.

## Why HF Spaces?

The free tier gives 16 GB RAM, which comfortably fits PyTorch + sentence-transformers. Render and Fly free tiers cap at 512 MB and would OOM on first embedding call.
