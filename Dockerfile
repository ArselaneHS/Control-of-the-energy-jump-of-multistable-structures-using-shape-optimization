# syntax=docker/dockerfile:1.7
#
# Reproducible environment for: Shape-Optimization-of-Energy-Jump
#
# Build (requires BuildKit, which is default in modern Docker):
#   DOCKER_BUILDKIT=1 docker build \
#     --secret id=gh_token,env=GH_TOKEN \
#     -t shape-opt-energy-jump:latest .
#
# (export GH_TOKEN=<your GitHub PAT with repo read access> before building,
#  or use --secret id=gh_token,src=/path/to/token_file instead)
#
# Run:
#   docker run -it --rm shape-opt-energy-jump:latest

# ---------------------------------------------------------------------------
# Pin this to a digest before publishing alongside the paper, e.g.:
#   docker pull fireshape/fireshape:latest
#   docker inspect --format='{{index .RepoDigests 0}}' fireshape/fireshape:latest
# then replace the line below with:
#   FROM fireshape/fireshape@sha256:<digest>
# ---------------------------------------------------------------------------
FROM fireshape/fireshape@sha256:fd31374c80b3191074739bf4669c38221e0276c624dd6b375ea76faa3fcffd36

# Firedrake version pinned for this project's results.
ARG FIREDRAKE_TAG=2025.10.2

# Persist the env vars you were exporting manually per-terminal.
ENV PYTHONPATH=/usr/local/lib/python3.12/site-packages:${PYTHONPATH}
ENV PATH="/root/.local/bin:${PATH}"

# ---------------------------------------------------------------------------
# System dependencies (stable, changes rarely -> keep early for layer cache)
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    xkb-data \
    wget \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# ParaView 6.1.0 (large, stable -> keep early)
# ---------------------------------------------------------------------------
WORKDIR /opt
RUN wget -O paraview-6.1.0.tar.gz \
    "https://www.paraview.org/paraview-downloads/download.php?submit=Download&version=v6.1&type=binary&os=Linux&downloadFile=ParaView-6.1.0-MPI-Linux-Python3.12-x86_64.tar.gz" \
    && tar -xzf paraview-6.1.0.tar.gz \
    && rm paraview-6.1.0.tar.gz

ENV PATH="/opt/ParaView-6.1.0-MPI-Linux-Python3.12-x86_64/bin:${PATH}"

# ---------------------------------------------------------------------------
# Pin Firedrake to the version used for the paper's results.
# firedrake-clean only purges the PyOP2/TSFC JIT cache; it does not reinstall
# the package. If your setup needs a rebuild/reinstall step after checkout,
# add it here (e.g. `pip install -e .`).
# ---------------------------------------------------------------------------
WORKDIR /opt/firedrake
RUN git fetch --all --tags \
    && git checkout ${FIREDRAKE_TAG} \
    && pip install --no-build-isolation -e . \
    && firedrake-clean

# ---------------------------------------------------------------------------
# defcon (deflated continuation library)
# ---------------------------------------------------------------------------
ARG DEFCON_COMMIT=12ce92e3112f91806740f4eed74b9f52cfbdb298
WORKDIR /opt
RUN git clone https://bitbucket.org/pefarrell/defcon.git \
    && git -C defcon checkout ${DEFCON_COMMIT} \
    && pip install --no-cache-dir ./defcon
# ---------------------------------------------------------------------------
# Project repo (private -> use a BuildKit secret so the token never lands in
# an image layer). Placed last so code changes don't invalidate the cache
# for everything above.
# ---------------------------------------------------------------------------
WORKDIR /opt
RUN --mount=type=secret,id=gh_token \
    git clone https://x-access-token:$(cat /run/secrets/gh_token)@github.com/ArselaneHS/Shape-Optimization-of-Energy-Jump.git project
# RUN git clone https://github.com/ArselaneHS/Shape-Optimization-of-Energy-Jump.git project

WORKDIR /opt/project

# Step 1: Filter out firedrake
RUN grep -v -i -E 'firedrake|netgen' requirements.txt > /tmp/reqs.txt

# Step 2: Install remaining requirements
RUN pip install --no-cache-dir --no-deps --no-build-isolation -r /tmp/reqs.txt

# Step 3: Install local project in editable mode
RUN pip install --no-cache-dir --no-deps -e .

CMD ["/bin/bash"]