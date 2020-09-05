
FROM datajoint/jupyter:python3.6

RUN pip install --upgrade pip

ADD . /src/datajoint-churchland
RUN pip install -e /src/datajoint-churchland