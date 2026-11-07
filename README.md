# vps-supervisor

Un piccolo deployer in stile Heroku/[Piku](https://github.com/piku/piku), con due differenze:

- **non si prende le porte 80/443**: l'agent installato sul server classifica
  lo stack web esistente (nginx, caddy, apache, haproxy, traefik, container
  Docker…) e ci aggancia le app;
- **un deployment = un file** (nome libero): host, dominio, build, porta, env,
  volumi… tutto esplicito in un unico YAML, invece di Procfile/ENV/… sparsi.

Un solo file Python (solo libreria standard, Python ≥ 3.8 su entrambi i lati):
sulla tua macchina fa da CLI, sul server fa da agent.

## Deploy

```sh
./vps-supervisor deploy examples/server-status/vps0.yafb.net.yml
./vps-supervisor deploy app.yml --check      # solo verifiche, nessun deploy
./vps-supervisor deploy app.yml --skip-dns   # deploy anche se il DNS non punta ancora qui
```

Fasi:

1. legge e valida il file di deployment;
2. si collega via SSH (installa `python3` se manca, su sistemi apt);
3. installa/aggiorna l'agent sul server e rifà il rilevamento; installa Docker se manca;
4. sceglie l'integrazione col proxy in base al caso classificato;
5. verifica che il dominio risolva sugli IP della macchina;
6. carica il contesto di build, builda l'immagine, sostituisce il container,
   fa l'health check (con **rollback** alla release precedente se fallisce);
7. verifica da fuori `https://<domain><healthcheck>`.

Altri comandi sul file di deployment: `logs app.yml`, `destroy app.yml`.

## File di deployment

```yaml
app: server-status            # nome (container vps-<app>)
runtime: docker               # docker (default) | host (previsto: app sulla macchina, es. systemd)
host: root@82.165.241.56      # oppure {ssh: ..., port: 22, identity: ~/.ssh/id_rsa}
domain: vps0.yafb.net
build: .                      # cartella col Dockerfile (relativa al file) — oppure:
# image: traefik/whoami:v1.10 # immagine da registry
port: 8000                    # porta dell'app dentro il container
healthcheck: /health
env:
  STATUS_TITLE: vps0
volumes:
  - /etc/hostname:/host/hostname:ro
proxy:                        # opzionale: override dei parametri rilevati
  network: proxy
  entrypoint: websecure
  certresolver: le
```

In arrivo: variabili autogenerate al deploy (segreti, password, …).

## Casi di proxy classificati

| mode                  | quando                                          | deploy |
|-----------------------|-------------------------------------------------|--------|
| `traefik-docker`      | un container Traefik pubblica 80/443: si leggono network, entrypoint e certresolver dai suoi argomenti e l'app viene esposta con le label Docker | ✅ |
| `none`                | porte libere: app su `127.0.0.1:<porta>`        | ✅ |
| `manual`              | porte occupate, proprietario non identificabile: app su `127.0.0.1:<porta>` | ✅ |
| `nginx` / `caddy` / `apache` / `haproxy` / `traefik` | quel processo ascolta su 80/443 | rilevato, non ancora deployabile |
| `caddy-docker`, `nginx-proxy-docker`, `npm-docker`, `docker-container` | un altro container pubblica 80/443 | rilevato, non ancora deployabile |

## Gestione host

```sh
./vps-supervisor install   root@host   # installa/aggiorna l'agent (/opt/vps-supervisor o ~/.vps-supervisor)
./vps-supervisor status    root@host   # config, caso proxy, app deployate
./vps-supervisor detect    root@host   # rifà il rilevamento (--json per l'output completo)
./vps-supervisor uninstall root@host
```

## Esempi

Vedi [`examples/`](examples/).
