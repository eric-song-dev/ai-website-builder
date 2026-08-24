FROM postgres:16
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates postgresql-server-dev-16
COPY pgvector /tmp/pgvector
RUN make -C /tmp/pgvector OPTFLAGS="" \
    && make -C /tmp/pgvector install \
    && rm -rf /tmp/pgvector \
    && apt-get remove -y build-essential postgresql-server-dev-16 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*
