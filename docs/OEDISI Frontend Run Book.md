# OEDISI Frontend Run Book

Deploys the app behind nginx at `https://oedi.ornl.gov` with TLS + per-user HTTP
Basic auth. nginx handles TLS, serving static files, authentication, and forwarding /api requests.

## Requires

- SSL certificate (.pem) and key (.key)
- nginx, `npm`, and `uv` installed.
- Clone `oedisi-frontend-app` and `oedisi-components`.

## Frontend

1. Build the frontend so it calls the API same-origin:
   ```bash
   npm install
   VITE_API_URL=/api npm run build
   ```
   Output lands in `dist/`.

2. Edit `ssl_certificate` and `ssl_certificate_key` in `deploy/nginx.conf` to point to the `.pem` and `.key` TLS files.
   You will need to copy `dist/` to either `/srv/oedisi-frontend-app/dist` or an OS specific location for RHEL/Fedora.
3. Install the config:
   ```bash
   # Assuming ubuntu. This will be different depending on the OS.
   cp deploy/nginx.conf /etc/nginx/sites-available/oedisi
   ln -s /etc/nginx/sites-available/oedisi /etc/nginx/sites-enabled/oedisi
   ```
4. Create the user credentials (random passwords). Each new user also needs a template dir (Backend step 2).
   ```bash
   htpasswd -c /etc/nginx/oedisi.htpasswd alice   # -c creates the file (first user only)
   htpasswd    /etc/nginx/oedisi.htpasswd bob      # omit -c to append
   ```
5. Enable and reload:
   ```bash
   nginx -t  # check nginx config
   systemctl enable nginx  # If you haven't enabled nginx yet.
   systemctl reload nginx
   ```

## Backend

1. Sync deps in both `server/` and `oedisi-components/`:
   ```bash
   # In oedisi-frontend-app
   cd server && uv sync
   # In oedisi-components
   uv sync
   ```
2. Per user, seed templates from the dev set:
   ```bash
   # In oedisi-frontend-app
   cp -r data/templates/dev data/templates/alice
   ```
3. Install the backend as a service. Fill in the `TODO` fields (service user, working dir, `OEDISI_COMPONENTS`, path to `uv`),
   cp `deploy/oedisi-backend.service` to `/etc/systemd/system/`, then:
   ```bash
   systemctl daemon-reload
   systemctl enable --now oedisi-backend
   ```
   The unit binds `127.0.0.1:3001`; port 3001 must not be exposed externally.

To run it by hand instead (debugging), the unit's `ExecStart` line is the
equivalent one-off command.

## Verification

We can check the frontend nginx and Python backend with:

```bash
curl -u alice https://oedi.ornl.gov
curl -u alice https://oedi.ornl.gov/api/templates
```
