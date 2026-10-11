# iconvert

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

### Unraid icon URL

```
http://192.168.88.140:8000/convert.png?source=https://example.com/logo.svg
```

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
