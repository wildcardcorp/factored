FROM python:3.6-slim
LABEL Description="This image is used to start a Factored instance" \
      Vendor="Wildcard Corp." \
      Version="1.0"

# the deps for ldap integration will be installed right away too
RUN apt-get -y update && apt-get -y install \
    libldap2-dev \
    libsasl2-dev \
    libsqlite3-dev

COPY docker-entrypoint.sh /

RUN mkdir /app /data
WORKDIR /app

COPY . /app
RUN pip install -r requirements.docker.txt

