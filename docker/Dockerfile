FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y curl perl build-essential git
# VEP install stub – Claude to append full commands.
COPY . /app
WORKDIR /app
RUN pip install poetry && poetry install --no-root
ENTRYPOINT ["poetry", "run", "python", "cli.py"]
