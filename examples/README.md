# Esempi

Ogni esempio ha il suo file di deployment YAML (il nome è libero).

| esempio          | file                 | tipo                         | porta |
|------------------|----------------------|------------------------------|-------|
| `server-status`  | `vps0.yafb.net.yml`  | Dockerfile, Python stdlib — stato del server | 8000 |
| `whoami-image`   | `deploy.yml`         | solo immagine Docker         | 80    |
| `static-site`    | `deploy.yml`         | Dockerfile, nginx            | 80    |
| `python-flask`   | `deploy.yml`         | Dockerfile, gunicorn         | 8000  |
| `node-http`      | `deploy.yml`         | Dockerfile, zero deps        | 3000  |

Nei `deploy.yml` cambia `host` e `domain`, poi:

```sh
./vps-supervisor deploy examples/node-http/deploy.yml
```
