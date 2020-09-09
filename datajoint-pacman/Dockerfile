
FROM datajoint/jupyter:python3.6

RUN pip install --upgrade pip

ADD . /src/datajoint-pacman

RUN pip install -e /src/datajoint-pacman

RUN pip install datajoint-churchland