"""Check imports and --help without distributing restricted SMPL-H assets.

Both upstream projects instantiate SMPL-H at import time, before parsing
--help. The mock is confined to this smoke-test process and must never be used
for model inference.
"""
import runpy
import sys

import smplx
import torch

if len(sys.argv) != 2:
    raise SystemExit('usage: check_entrypoint.py MODULE')
module = sys.argv[1]
smplx.create = lambda *args, **kwargs: torch.nn.Identity()
print(f'Checking {module} --help with SMPL-H creation mocked', flush=True)
sys.argv = [module, '--help']
runpy.run_module(module, run_name='__main__')
