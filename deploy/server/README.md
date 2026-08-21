# NoteSolve server deployment

This deployment consumes prebuilt `linux/amd64` and `linux/arm64` images from GitHub Container
Registry. The server does not need Node.js, Python, pnpm, uv, or the source tree to run NoteSolve.

## 1. Publish images

Run the `Publish container images` workflow from GitHub Actions with tag `edge` for a development
deployment. Pushes to `main` publish `latest`; version tags such as `v0.1.0` publish an immutable
version tag. The workflow runs backend and frontend checks before publishing both images.

Make the two GHCR packages public, or authenticate the server with a GitHub token that has
`read:packages` permission before pulling private images.

## 2. Prepare the server

Install Docker Engine with the Compose plugin, then create persistent directories owned by the
non-root UID/GID used by the API image:

```bash
sudo mkdir -p /opt/notesolve/{data,vault}
sudo chown -R 10001:10001 /opt/notesolve/data /opt/notesolve/vault
```

Copy this directory to `/opt/notesolve/deploy`, create `.env.server` from
`.env.server.example`, and set the OpenAI key. Restrict the secret file:

```bash
cp .env.server.example .env.server
chmod 600 .env.server
```

Keep `NOTESOLVE_BIND_ADDRESS=127.0.0.1`. NoteSolve does not yet provide application-level user
authentication and must not be exposed directly to the public internet.

## 3. Deploy and verify

```bash
./deploy.sh
./smoke-test.sh
```

For private remote access, install Tailscale on the server and client, then proxy the loopback
service with Tailscale Serve. This avoids opening the NoteSolve port in the cloud firewall.

## 4. Backup

`backup.sh` uses SQLite's online backup API and creates a compressed Vault archive. Both files are
written to `/data/backups` and therefore survive container replacement.

```bash
./backup.sh
```

Example daily cron entry:

```cron
15 3 * * * /opt/notesolve/deploy/backup.sh >> /opt/notesolve/backup.log 2>&1
```

Copy backups to a second machine or object store. A backup on the same VM is not sufficient for
disk or account failure.

## 5. Update and roll back

Deploy the tag selected in `.env.server`:

```bash
./deploy.sh
```

Temporarily roll back to an existing immutable tag:

```bash
./rollback.sh v0.1.0
```

After validation, persist that tag as `NOTESOLVE_IMAGE_TAG` in `.env.server`. Never use
`docker compose down -v` as a routine shutdown command. Server storage uses host bind mounts, but
the same command is still an unsafe habit for other Compose deployments.

