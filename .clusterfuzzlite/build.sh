#!/bin/bash -eu

cd "$SRC/agent-assurance-case"

for fuzzer in fuzz/*_fuzzer.py; do
  fuzzer_basename="$(basename -s .py "$fuzzer")"
  fuzzer_package="${fuzzer_basename}.pkg"

  pyinstaller \
    --paths "$SRC/agent-assurance-case" \
    --distpath "$OUT" \
    --onefile \
    --name "$fuzzer_package" \
    "$fuzzer"

  cat > "$OUT/$fuzzer_basename" <<EOF
#!/bin/sh
# LLVMFuzzerTestOneInput for fuzzer detection.
this_dir=\$(dirname "\$0")
\$this_dir/$fuzzer_package "\$@"
EOF
  chmod +x "$OUT/$fuzzer_basename"
done
