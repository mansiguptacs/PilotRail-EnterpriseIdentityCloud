FROM ubuntu:24.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    openssh-server \
    python3 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash developer \
    && mkdir -p /var/run/sshd /home/developer/.ssh

COPY ssh/authorized_keys /home/developer/.ssh/authorized_keys
COPY pilot-rail-hint.sh /etc/profile.d/pilot-rail-hint.sh
RUN chown -R developer:developer /home/developer/.ssh \
    && chmod 700 /home/developer/.ssh \
    && chmod 600 /home/developer/.ssh/authorized_keys \
    && printf '\n# Pilot Rail — load enterprise gate after IT deploy\n[ -f "$HOME/.pilot-rail/enable-gate.sh" ] && . "$HOME/.pilot-rail/enable-gate.sh"\n' >> /home/developer/.profile \
    && chown developer:developer /home/developer/.profile

WORKDIR /home/developer

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
