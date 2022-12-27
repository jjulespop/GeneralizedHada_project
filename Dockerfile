FROM python:3.8-slim-bullseye

WORKDIR /hada
COPY core ./core
COPY algorithms ./algorithms
COPY app.py .
COPY templates ./templates
COPY static ./static
COPY requirements.txt .

COPY cplex_studio2210.linux_x86_64.bin .
RUN ./cplex_studio2210.linux_x86_64.bin -DLICENSE_ACCEPTED=true -i silent
RUN python /opt/ibm/ILOG/CPLEX_Studio221/python/setup.py install

RUN pip install -r requirements.txt

ENTRYPOINT ["flask", "run", "--host=0.0.0.0"]
