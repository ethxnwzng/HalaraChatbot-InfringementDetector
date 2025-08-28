FROM hub.intra.doublefs.com/sys/baseimage/python:3.9
WORKDIR /app
COPY requirements.txt ./
ARG PIP
ENV PIP_INDEX_URL ${PIP}
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
