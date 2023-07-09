FROM ubuntu:22.04
RUN apt-get update -y  &&  apt-get install -y wget curl jq
RUN mkdir -p --mode=0755 /usr/share/keyrings
RUN curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg |  tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
RUN echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | tee /etc/apt/sources.list.d/cloudflared.list
RUN  apt-get update && apt-get install cloudflared
