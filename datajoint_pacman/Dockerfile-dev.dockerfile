
FROM datajoint/jupyter:python3.6

RUN pip install --upgrade pip

ADD . /src/datajoint-pacman

RUN pip install -e /src/datajoint-pacman

RUN mkdir -p /src \
    && cd /src \
    && git clone https://github.com/ZuckermanBrain/datajoint-churchland.git \
    && pip install -e /src/datajoint-churchland

ENV PATH /src/brPY:$PATH