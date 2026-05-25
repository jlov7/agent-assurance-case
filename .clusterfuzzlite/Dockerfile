FROM gcr.io/oss-fuzz-base/base-builder-python

COPY . $SRC/agent-assurance-case
COPY .clusterfuzzlite/build.sh $SRC/build.sh
WORKDIR $SRC/agent-assurance-case

RUN pip3 install --no-cache-dir \
    -r verifier/requirements.txt \
    atheris \
    pyinstaller \
    && chmod +x "$SRC/build.sh"
