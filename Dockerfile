FROM python:3.11.6

RUN mkdir -p /usr/src

WORKDIR /usr/src

COPY requirements.txt ./

COPY .autodevops/.build/pip.conf /root/.config/pip/

RUN pip install -r requirements.txt

RUN rm -rf /root/.config

COPY /src ./

ENTRYPOINT python main.py