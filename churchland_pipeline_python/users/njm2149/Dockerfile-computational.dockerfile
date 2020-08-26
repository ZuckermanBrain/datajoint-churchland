
FROM datajoint/jupyter:python3.6

RUN pip install --upgrade pip

ADD .. /src/datajoint-njm2149

RUN pip install -e /src/datajoint-njm149