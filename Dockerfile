FROM python:3.8-slim-bullseye

COPY cplex_studio2210.linux_x86_64.bin .
RUN ./cplex_studio2210.linux_x86_64.bin -DLICENSE_ACCEPTED=true -i silent
RUN python /opt/ibm/ILOG/CPLEX_Studio221/python/setup.py install

WORKDIR /hada

COPY requirements.txt .
RUN pip install -r requirements.txt

# emllib bug fix
COPY embed.py /usr/local/lib/python3.8/site-packages/eml/tree/embed.py

COPY core ./core
COPY algorithms ./algorithms
COPY app.py .
COPY templates ./templates
COPY static ./static

ENTRYPOINT ["flask", "run", "--host=0.0.0.0"]
