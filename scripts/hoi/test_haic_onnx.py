"""Run the seven released HAIC ONNX policies on CPU with synthetic inputs."""
from pathlib import Path
import numpy as np
import onnxruntime as ort

options = ort.SessionOptions()
options.intra_op_num_threads = 4
policies = sorted(Path('/models/haic/haic').rglob('*.onnx'))
assert len(policies) == 7
for path in policies:
    session = ort.InferenceSession(str(path), options, providers=['CPUExecutionProvider'])
    inputs = {}
    for item in session.get_inputs():
        shape = [d if isinstance(d, int) else 1 for d in item.shape]
        assert item.type == 'tensor(float)', (item.name, item.type)
        inputs[item.name] = np.zeros(shape, dtype=np.float32)
    outputs = session.run(None, inputs)
    assert outputs and all(np.isfinite(value).all() for value in outputs)
    print(path.parent.name, 'ONNX forward passed', [list(o.shape) for o in outputs], flush=True)
