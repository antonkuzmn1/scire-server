# storage-server


# quick start:
```bash
cp .env.template .env
```
```bash
alembic revision --autogenerate -m "initial migration"
```
```bash
alembic upgrade head
```