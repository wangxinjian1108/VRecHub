"""Validate Kimodo denoiser and local text assets without loading the 8B encoder."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import json
from pathlib import Path
import torch
from safetensors import safe_open
from transformers import AutoConfig, AutoTokenizer
from kimodo import load_model

# Only the motion network is exercised here. Full text conditioning is tested
# separately on the target machine, which has more memory than a hosted runner.
model = load_model('kimodo-soma-rp', device='cpu', text_encoder=torch.nn.Identity())
assert sum(p.numel() for p in model.denoiser.parameters()) > 100_000_000
root = Path('/models/text-encoders')
base = root / 'meta-llama/Meta-Llama-3-8B-Instruct'
config = AutoConfig.from_pretrained(base, local_files_only=True)
tokenizer = AutoTokenizer.from_pretrained(base, local_files_only=True)
assert config.hidden_size == 4096 and tokenizer('a person walks')['input_ids']
index = json.loads((base / 'model.safetensors.index.json').read_text())
keys = set()
for filename in set(index['weight_map'].values()):
    with safe_open(base / filename, framework='pt', device='cpu') as weights:
        keys.update(weights.keys())
assert keys == set(index['weight_map'])
for name in ['LLM2Vec-Meta-Llama-3-8B-Instruct-mntp', 'LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised']:
    folder = root / 'McGill-NLP' / name
    adapter = json.loads((folder / 'adapter_config.json').read_text())
    assert adapter['base_model_name_or_path'] == str(base)
    with safe_open(folder / 'adapter_model.safetensors', framework='pt') as weights:
        assert len(weights.keys()) > 100
print('Kimodo denoiser loaded; Llama shards, tokenizer and both local adapters verified')
