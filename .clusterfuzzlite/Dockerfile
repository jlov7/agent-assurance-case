FROM gcr.io/oss-fuzz-base/base-builder-python

COPY . $SRC/agent-assurance-case
WORKDIR $SRC/agent-assurance-case

RUN pip3 install --no-cache-dir \
    -r verifier/requirements.txt \
    atheris \
    pyinstaller
