# Rule: Render Deployment Protocol — GitHub Auto-Deploy Only (Zero API Triggers)

## Summary
Render web service `srv-dabdp2rtqb8s73fjp000` (`echosphere-backend`) has `autoDeploy: yes` permanently enabled. GitHub push events to `origin/main` automatically and authoritatively trigger Render builds. Triggering deployments via the Render REST API is strictly forbidden.

## Mandated Deployment Protocol
1. **GitHub is the Sole Deployment Trigger**:
   - The only valid action to initiate a deployment is `git push origin main`.
   - Render's GitHub webhook fires automatically upon receiving commits on the `main` branch.
2. **Strict Prohibition of API Deploy Triggers**:
   - NEVER call `POST https://api.render.com/v1/services/{serviceId}/deploys`.
   - NEVER script, invoke, or trigger manual deployments via the Render REST API.
   - Calling deploy endpoints creates duplicate, concurrent build queues that collide with GitHub's automatic webhook pipeline.
3. **Passive Monitoring Only**:
   - When monitoring a deployment after `git push`, use read-only inspection endpoints:
     - `GET /v1/services/{serviceId}/deploys` (read deploy state)
     - `GET /v1/logs` (read build logs)
     - `GET https://echosphere-backend-9lv8.onrender.com/api/v1/ai/router/status` (verify live health)
   - Never interfere with Render's native GitHub build queue.

## Secrets Protection Guarantee
- NEVER commit or push API keys (Render, Hugging Face, Supabase, JWT) to Git.
- Local untracked `.env` files and `scratch/` directories must remain strictly `.gitignored`.
