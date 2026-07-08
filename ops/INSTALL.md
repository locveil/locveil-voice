# Installing Irene on a Wirenboard controller

The controller runs prebuilt images pulled from the GitHub Container Registry — it never builds
anything. This directory is the whole deployment: a compose file, a short update script, and a
systemd unit. The pattern (and most of the muscle memory) is the same as the sibling
`wb-mqtt-bridge` deployment.

**Disk layout: the clone on the SD card is the delivery vehicle; `/mnt/data` holds the runtime
tree the container mounts** — the same split as the sibling bridge deployment:

```
/mnt/sdcard/wb-mqtt-voice/         <- this repo, cloned (compose, update.sh, .env)
/mnt/data/mqtt-voice-config/       <- the RUNTIME tree the container mounts
├── assets/                        <- /app/assets: synced git-owned content (donations,
│                                     prompts, templates, localization) + downloaded speech
│                                     models, cache, traces, durable state (state/)
└── logs/                          <- /app/logs: irene.log + timestamped rotations
```

`update.sh` bridges the two: it rsyncs the git-owned assets subtrees from the clone into the
runtime tree (and only those — models and state are never touched), so `git pull` is how
content updates reach the controller. Docker's data-root is already configured on the
controller (`/mnt/data/.docker`) and stays where it is.

## Install

```sh
cd /mnt/sdcard
git clone https://github.com/droman42/wb-mqtt-voice.git
cd wb-mqtt-voice/ops
./update.sh            # creates + syncs the runtime tree, pulls images, starts the stack
```

Then wire it to boot:

```sh
ln -s /mnt/sdcard/wb-mqtt-voice/ops/wb-mqtt-voice.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wb-mqtt-voice
```

The web API answers on port **8080** (`curl http://localhost:8080/health`). Speech models
download into the runtime tree's `assets/` on first boot — the first start takes a few
minutes; subsequent starts reuse them.

## Secrets

Two optional cloud integrations read their keys from the container's environment; both degrade
cleanly to "off" when the key is absent (the assistant still runs fully offline):

- `DEEPSEEK_API_KEY` — the cloud LLM tier of intent recognition;
- `IRENE_REPORTS_TOKEN` — the GitHub token that lets spoken problem reports file themselves
  (fine-grained PAT for the private reports repo, Issues + Contents read/write).

Put them in an `ops/.env` file next to the compose file — compose reads it automatically on
both start paths (the systemd unit and `update.sh` run compose from this directory):

```sh
cat > /mnt/sdcard/wb-mqtt-voice/ops/.env <<'EOF'
DEEPSEEK_API_KEY=sk-XXXXXXXX
IRENE_REPORTS_TOKEN=github_pat_XXXXXXXX
EOF
chmod 600 /mnt/sdcard/wb-mqtt-voice/ops/.env
```

The file is gitignored; `git pull` never touches it. After adding or changing it, re-run
`docker compose up -d` (or `./update.sh`).

## Update

```sh
cd /mnt/sdcard/wb-mqtt-voice
git pull
./ops/update.sh
```

`update.sh` re-syncs the git-owned assets subtrees (and **only** those — downloaded models and
runtime state are never touched), fixes ownership for the container user, pulls the newest
images, restarts the stack, and prunes old image layers to keep flash usage in check.

## Rolling back

Every published image also carries an immutable `vYYYYMMDD-<sha>` tag (see the package pages on
GHCR). Pin it in `docker-compose.yml`:

```yaml
    image: ghcr.io/droman42/wb-mqtt-voice-armv7:v20260702-abc1234
```

and run `docker compose up -d`. Return to `:latest` the same way.

## Variants

- **aarch64 controller (WB8.5 / Pi)** — switch the image to the aarch64 build
  (`ghcr.io/droman42/wb-mqtt-voice-aarch64`); everything else is identical. The armv7 default
  in the compose file targets the WB7.
- **English deployment** — switch the image to the `-en` variant
  (`ghcr.io/droman42/wb-mqtt-voice-armv7-en` / `-aarch64-en`); language is baked into the
  image, nothing else changes.
- **The configuration editor** — not part of the standard deployment. Bring it up on demand:

  ```sh
  docker compose --profile ui up -d      # serves on port 3000, talks to Irene on :8080
  docker compose --profile ui down       # and away again
  ```

## Satellite TLS plane (optional)

Room satellites that connect over mutual TLS (`wss://`) need the fleet-provisioning plane —
nginx + a tiny home CA serving the certificate bootstrap and the mTLS gate. It deliberately
runs **outside** this container, directly on the controller (security-critical PKI must not
depend on Irene being up). It is deployed separately, via ansible — see
[`nginx/README.md`](../nginx/README.md) for the design, the operator runbook
(`esp32-provision approve …`) and the deploy playbook. One wiring point connects the two
planes: set `esp32_irene_upstream: 127.0.0.1:8080` in the nginx `group_vars` so `/ws/audio*`
proxies to the container installed here. Satellites on a trusted network can skip all of this
and connect over plain `ws://` directly to :8080.

## Recovery notes

- The container is stateless: removing it (or the image) loses nothing — everything that matters
  lives in the runtime tree and the git clone.
- **An SD card death loses nothing precious.** The card only carries the clone (and `ops/.env` —
  keep your keys somewhere safe): re-clone, recreate `.env`, re-run `./update.sh`. The whole
  runtime tree — models, durable state, logs — sits on `/mnt/data` and reattaches as-is.
- A corrupted model download can be deleted from
  `/mnt/data/mqtt-voice-config/assets/models/…`; it re-downloads on the next start.
- Memory: the compose file caps Irene at 800 MB — if the assistant is OOM-killed on a busy
  controller, check `docker stats` and tune the cap (the ASR/TTS models are the big consumers).
