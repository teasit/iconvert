<p align="center"><img src="logo.svg" alt="iconvert logo" width="128"></p>

<h1 align="center">iconvert</h1>

Tiny HTTP service that fetches an image from a URL and returns it converted to
another format — built for Unraid, whose Docker icons must be PNG while many
projects only publish SVG logos.

Powered by [libvips](https://www.libvips.org/) (SVG is rendered at the target
size, so icons stay crisp), with a Pillow fallback for formats like `.ico`.

## Usage

```
GET /convert.png?source=<url>&size=256
GET /convert?source=<url>&format=png&size=256
GET /health
```

| Param    | Default | Notes                                                        |
|----------|---------|--------------------------------------------------------------|
| `source` | —       | http(s) URL of the input image (SVG, PNG, JPG, WebP, GIF, ICO, AVIF, TIFF…). URL-encode it if it contains `?` or `&`. |
| `format` | `png`   | `png`, `jpg`, `webp`, `gif`, `tiff`, `avif` (or use the `/convert.<ext>` form) |
| `size`   | `256`   | Longest edge in px, 16 – `MAX_SIZE`                          |
| `bg`     | none    | 6-digit hex background, e.g. `ffffff`. JPG defaults to white. |

Results are cached on disk in `/cache`, keyed by all parameters.

Examples, using this repo's own logo as the source:

```sh
# SVG -> 256 px PNG
curl -o logo.png "http://localhost:8000/convert.png?source=https://raw.githubusercontent.com/teasit/iconvert/main/logo.svg"
# SVG -> 64 px WebP
curl -o logo.webp "http://localhost:8000/convert.webp?source=https://raw.githubusercontent.com/teasit/iconvert/main/logo.svg&size=64"
# SVG -> JPG on a black background
curl -o logo.jpg "http://localhost:8000/convert?source=https://raw.githubusercontent.com/teasit/iconvert/main/logo.svg&format=jpg&bg=000000"
```

### Unraid icon URL

```
http://localhost:8000/convert.png?source=https://raw.githubusercontent.com/teasit/iconvert/main/logo.svg
```

Unraid downloads container icons on the server itself, so `localhost` works
when iconvert's port is published on the Unraid host, i.e. the container uses
the **bridge** network with `8000:8000` (or **host** networking). On a custom
network where the container gets its own IP (`br0`, macvlan/ipvlan) use that
IP instead, e.g. `http://192.168.88.140:8000/convert.png?source=…` — the host
usually can't reach such containers, so bridge is recommended.

- Include `http://`.
- Prefer the `/convert.png` form so the URL ends in `.png`.
- Unraid caches icons in `/var/lib/docker/unraid/images/`; delete the
  container's file there if an icon doesn't refresh.

## Running

```sh
docker compose up -d --build
# or
docker build -t iconvert .
docker run -d -p 8000:8000 -v /mnt/user/appdata/iconvert:/cache iconvert
```

An Unraid template is in [`unraid/iconvert.xml`](unraid/iconvert.xml).

### Environment

| Variable        | Default    | Description                                         |
|-----------------|------------|-----------------------------------------------------|
| `ALLOWED_HOSTS` | (any)      | Comma-separated hostnames allowed as `source`       |
| `MAX_SIZE`      | `2048`     | Maximum `size` value                                |
| `MAX_BYTES`     | `10485760` | Maximum source download size                        |
| `FETCH_TIMEOUT` | `10`       | Source fetch timeout, seconds                       |
| `CACHE_DIR`     | `/cache`   | Cache directory                                     |

Intended for trusted LANs: it will fetch any http(s) URL it's given unless
`ALLOWED_HOSTS` is set.
