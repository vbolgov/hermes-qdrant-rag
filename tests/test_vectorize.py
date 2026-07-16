import json
import subprocess
import sys


def test_hash_embedding_is_stable_across_python_processes():
    code = "from vectorize import embed_text; import json; print(json.dumps(embed_text('vitamin d fatigue sleep stress ferritin analysis client history')))"
    outputs = {
        subprocess.check_output([sys.executable, "-c", code], text=True)
        for _ in range(8)
    }
    assert len(outputs) == 1
