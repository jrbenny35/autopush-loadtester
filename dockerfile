FROM alpine:latest

# deps
RUN apk add --update python3; \
    apk add --update py-pip; \
    apk add --update python3-dev; \
    apk add --update openssl-dev; \
    apk add --update libffi-dev; \
    apk add --update build-base; \
    apk add --update git; \
    pip install --upgrade pip;

WORKDIR /code
ADD . /code

RUN pip install -r requirements.txt

CMD  molotov --use-extension tests/config.py -v --single-run tests/loadtests.py