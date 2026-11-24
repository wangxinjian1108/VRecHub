"""Render and check a small image with Blender's CPU Cycles renderer."""
from pathlib import Path

import bpy

scene = bpy.context.scene
assert scene.camera is not None, 'default scene has no camera'
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 4
scene.render.resolution_x = 64
scene.render.resolution_y = 64
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = '/tmp/hoi-blender-check.png'
bpy.ops.render.render(write_still=True)

output = Path(scene.render.filepath)
assert output.is_file() and output.stat().st_size > 256
image = bpy.data.images.load(str(output), check_existing=False)
assert tuple(image.size) == (64, 64)
pixels = list(image.pixels)
assert max(pixels[0::4]) - min(pixels[0::4]) > 0.05, 'render is uniform'
print(f'Blender {bpy.app.version_string}: headless CPU render verified')
