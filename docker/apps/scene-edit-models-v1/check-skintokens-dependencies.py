"""Keep dependency checks strict except for bpy's incorrect internal wheel tag."""

import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pip", "check"], capture_output=True, text=True
)
print(result.stdout, end="")
print(result.stderr, end="", file=sys.stderr)

# PyPI's bpy-4.5.3-cp311-cp311-manylinux_2_28_x86_64.whl contains an
# incorrect cp39-cp39 tag in .dist-info/WHEEL. Its filename and Requires-Python
# correctly specify CPython 3.11. Allow only this exact diagnostic; any other
# missing/incompatible dependency or pip failure still fails the build.
known_diagnostic = "bpy 4.5.3 is not supported on this platform"
if result.returncode and (
    result.returncode != 1
    or result.stdout.strip() != known_diagnostic
    or result.stderr.strip()
):
    raise SystemExit(result.returncode)

import bpy

assert bpy.app.version == (4, 5, 3), bpy.app.version
print("bpy 4.5.3 imports successfully on CPython", sys.version.split()[0])
