import os

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

from testcontainers.postgres import PostgresContainer

postgres = PostgresContainer("postgres:16")
postgres.start()

os.environ["POSTGRES_DB"] = postgres.dbname
os.environ["POSTGRES_USER"] = postgres.username
os.environ["POSTGRES_PASSWORD"] = postgres.password
os.environ["POSTGRES_HOST"] = postgres.get_container_host_ip()
os.environ["POSTGRES_PORT"] = str(postgres.get_exposed_port(5432))

from config.settings import *  # noqa: E402,F403
