#!/usr/bin/env python3
"""
Blender Material Generator
Builds procedural materials from visual specifications in the unified asset registry.
"""

import bpy
import json
import sys
import os
import colorsys
import math

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def hex_to_rgb(hex_str):
    """Convert '#RRGGBB' to linear RGB (0-1)."""
    hex_str = hex_str.lstrip("#")
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return (r, g, b)


def adjust_contrast(color, level):
    """Rudimentary contrast adjustment for a single RGB tuple."""
    r, g, b = color
    # convert to HSV for simple contrast-ish tweak on V
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if level == "low":
        v = 0.4 + (v - 0.5) * 0.5
    elif level == "medium":
        v = v
    elif level == "high":
        v = 0.5 + (v - 0.5) * 1.5
    v = max(0.0, min(1.0, v))
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return (r2, g2, b2)


def clear_material_nodes(mat):
    """Clear all nodes from a material."""
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    for n in list(nodes):
        nodes.remove(n)


# ------------------------------------------------------------
# Shape-Aware Material Variations
# ------------------------------------------------------------

def get_shape_hints(shape_description):
    """Extract hints from shape description for material tuning."""
    shape_lower = shape_description.lower()
    hints = {
        "noise_scale": 10.0,
        "voronoi_scale": 15.0,
        "pattern_type": "organic"
    }
    
    if "spiral" in shape_lower or "swirl" in shape_lower:
        hints["pattern_type"] = "spiral"
        hints["noise_scale"] = 8.0
        hints["voronoi_scale"] = 12.0
    elif "burst" in shape_lower or "explosion" in shape_lower:
        hints["pattern_type"] = "radial"
        hints["noise_scale"] = 15.0
        hints["voronoi_scale"] = 20.0
    elif "leaf" in shape_lower or "organic" in shape_lower:
        hints["pattern_type"] = "organic"
        hints["noise_scale"] = 12.0
        hints["voronoi_scale"] = 18.0
    elif "shard" in shape_lower or "crystal" in shape_lower:
        hints["pattern_type"] = "geometric"
        hints["noise_scale"] = 20.0
        hints["voronoi_scale"] = 25.0
    elif "web" in shape_lower or "net" in shape_lower:
        hints["pattern_type"] = "network"
        hints["noise_scale"] = 5.0
        hints["voronoi_scale"] = 10.0
    elif "star" in shape_lower or "glyph" in shape_lower:
        hints["pattern_type"] = "symbolic"
        hints["noise_scale"] = 6.0
        hints["voronoi_scale"] = 8.0
    
    return hints


# ------------------------------------------------------------
# Style-specific builders
# ------------------------------------------------------------

def build_painterly_material(mat, icon_data):
    """
    Painterly style: soft gradients, noise, color ramp.
    Uses icon_data: shape, palette, contrast, lighting.
    """
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Basic nodes
    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    colorramp = nodes.new("ShaderNodeValToRGB")
    mix_rgb = nodes.new("ShaderNodeMixRGB")
    mapping = nodes.new("ShaderNodeMapping")
    tex_coord = nodes.new("ShaderNodeTexCoord")

    output.location = (600, 0)
    principled.location = (400, 0)
    mix_rgb.location = (200, 0)
    colorramp.location = (0, 0)
    noise.location = (-200, 100)
    voronoi.location = (-200, -100)
    mapping.location = (-400, 0)
    tex_coord.location = (-600, 0)

    # Get shape hints
    shape = icon_data.get("shape", "magical symbol")
    shape_hints = get_shape_hints(shape)
    
    # Apply shape-based tuning
    noise.inputs["Scale"].default_value = shape_hints["noise_scale"]
    noise.inputs["Detail"].default_value = 5.0
    voronoi.inputs["Scale"].default_value = shape_hints["voronoi_scale"]
    
    # Palette into color ramp
    palette = icon_data.get("palette", [])
    contrast = icon_data.get("contrast", "medium")

    # Ensure at least 2 ramp elements
    while len(colorramp.color_ramp.elements) < 2:
        colorramp.color_ramp.elements.new(0.5)

    # Clamp to 4 elements max for sanity
    max_ramp = min(4, len(palette)) if palette else 2
    for i, hex_color in enumerate(palette[:max_ramp]):
        col = hex_to_rgb(hex_color)
        col = adjust_contrast(col, contrast)
        if i == 0:
            elem = colorramp.color_ramp.elements[0]
            elem.position = 0.0
        elif i == 1:
            elem = colorramp.color_ramp.elements[1]
            elem.position = 1.0
        else:
            elem = colorramp.color_ramp.elements.new(i / (max_ramp - 1))
        elem.color = (*col, 1.0)

    # Some defaults if no palette
    if not palette:
        elem0 = colorramp.color_ramp.elements[0]
        elem1 = colorramp.color_ramp.elements[1]
        elem0.color = (0.2, 0.2, 0.25, 1)
        elem1.color = (0.6, 0.8, 0.6, 1)

    # Connect coords
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])

    # Combine noise + voronoi based on pattern type
    mix_rgb.blend_type = "MIX"
    mix_rgb.inputs["Fac"].default_value = 0.4
    
    if shape_hints["pattern_type"] == "radial":
        # For bursts, use voronoi distance more
        mix_rgb.inputs["Fac"].default_value = 0.6
        links.new(voronoi.outputs["Distance"], mix_rgb.inputs[1])
        links.new(noise.outputs["Fac"], mix_rgb.inputs[2])
    elif shape_hints["pattern_type"] == "spiral":
        # For spirals, combine both
        links.new(noise.outputs["Fac"], mix_rgb.inputs[1])
        links.new(voronoi.outputs["Distance"], mix_rgb.inputs[2])
    else:
        # Default: noise primary
        links.new(noise.outputs["Fac"], mix_rgb.inputs[1])
        links.new(voronoi.outputs["Distance"], mix_rgb.inputs[2])

    # Drive colorramp from mix
    links.new(mix_rgb.outputs["Color"], colorramp.inputs["Fac"])

    # Plug into principled
    links.new(colorramp.outputs["Color"], principled.inputs["Base Color"])

    # Slight roughness and specular
    principled.inputs["Roughness"].default_value = 0.6
    principled.inputs["Specular"].default_value = 0.2

    # Optional rim lighting (simple fake via geometry / layer weight)
    lighting = icon_data.get("lighting", "").lower()
    if "rim" in lighting or icon_data.get("glow", False):
        layer_weight = nodes.new("ShaderNodeLayerWeight")
        rim_mix = nodes.new("ShaderNodeMixRGB")
        layer_weight.location = (0, 200)
        rim_mix.location = (200, 200)

        rim_mix.blend_type = "ADD"
        rim_mix.inputs["Fac"].default_value = 0.7

        links.new(layer_weight.outputs["Facing"], rim_mix.inputs["Fac"])
        links.new(colorramp.outputs["Color"], rim_mix.inputs["Color1"])
        rim_mix.inputs["Color2"].default_value = (1.0, 1.0, 1.0, 1.0)

        links.new(rim_mix.outputs["Color"], principled.inputs["Base Color"])

    links.new(principled.outputs["BSDF"], output.inputs["Surface"])


def build_pixel_material(mat, icon_data):
    """
    Pixel style: sharper, less smoothing, nearest-like look.
    Still uses procedural base, but tuned differently.
    """
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    output = nodes.new("ShaderNodeOutputMaterial")
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    colorramp = nodes.new("ShaderNodeValToRGB")
    mapping = nodes.new("ShaderNodeMapping")
    tex_coord = nodes.new("ShaderNodeTexCoord")

    output.location = (400, 0)
    diffuse.location = (200, 0)
    colorramp.location = (0, 0)
    voronoi.location = (-200, 0)
    mapping.location = (-400, 0)
    tex_coord.location = (-600, 0)

    # Get shape hints
    shape = icon_data.get("shape", "symbol")
    shape_hints = get_shape_hints(shape)
    
    palette = icon_data.get("palette", [])
    contrast = icon_data.get("contrast", "high")

    while len(colorramp.color_ramp.elements) < 2:
        colorramp.color_ramp.elements.new(0.5)

    max_ramp = min(4, len(palette)) if palette else 2
    for i, hex_color in enumerate(palette[:max_ramp]):
        col = hex_to_rgb(hex_color)
        col = adjust_contrast(col, contrast)
        if i == 0:
            elem = colorramp.color_ramp.elements[0]
            elem.position = 0.0
        elif i == 1:
            elem = colorramp.color_ramp.elements[1]
            elem.position = 1.0
        else:
            elem = colorramp.color_ramp.elements.new(i / (max_ramp - 1))
        elem.color = (*col, 1.0)

    if not palette:
        elem0 = colorramp.color_ramp.elements[0]
        elem1 = colorramp.color_ramp.elements[1]
        elem0.color = (0.1, 0.1, 0.1, 1)
        elem1.color = (0.9, 0.9, 0.9, 1)

    # Fewer cells -> larger chunky shapes
    voronoi.inputs["Scale"].default_value = shape_hints["voronoi_scale"] * 0.5

    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])
    links.new(voronoi.outputs["Distance"], colorramp.inputs["Fac"])
    links.new(colorramp.outputs["Color"], diffuse.inputs["Color"])
    links.new(diffuse.outputs["BSDF"], output.inputs["Surface"])


def build_flat_material(mat, icon_data):
    """Flat style: simple, solid colors with minimal variation."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    colorramp = nodes.new("ShaderNodeValToRGB")
    noise = nodes.new("ShaderNodeTexNoise")
    mapping = nodes.new("ShaderNodeMapping")
    tex_coord = nodes.new("ShaderNodeTexCoord")

    output.location = (400, 0)
    principled.location = (200, 0)
    colorramp.location = (0, 0)
    noise.location = (-200, 0)
    mapping.location = (-400, 0)
    tex_coord.location = (-600, 0)

    palette = icon_data.get("palette", [])
    if palette:
        # Use first color as base
        base_color = hex_to_rgb(palette[0])
        principled.inputs["Base Color"].default_value = (*base_color, 1.0)
    else:
        principled.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)

    # Minimal noise for slight variation
    noise.inputs["Scale"].default_value = 2.0
    noise.inputs["Detail"].default_value = 1.0

    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], colorramp.inputs["Fac"])
    
    if len(palette) > 1:
        col1 = hex_to_rgb(palette[0])
        col2 = hex_to_rgb(palette[1])
        colorramp.color_ramp.elements[0].color = (*col1, 1.0)
        colorramp.color_ramp.elements[1].color = (*col2, 1.0)
        links.new(colorramp.outputs["Color"], principled.inputs["Base Color"])

    principled.inputs["Roughness"].default_value = 0.8
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])


# ------------------------------------------------------------
# Node Group Creation (Export Mode)
# ------------------------------------------------------------

def create_node_group(name, inputs, outputs, build_fn):
    """
    Creates a reusable node group with specified inputs/outputs.
    
    Args:
        name: Name of the node group
        inputs: List of dicts with "name" and "type" keys
        outputs: List of dicts with "name" and "type" keys
        build_fn: Function that builds the internal node structure
    
    Returns:
        The created node group
    """
    # Check if group already exists
    if name in bpy.data.node_groups:
        group = bpy.data.node_groups[name]
        # Clear existing nodes
        for node in list(group.nodes):
            group.nodes.remove(node)
    else:
        group = bpy.data.node_groups.new(name=name, type="ShaderNodeTree")
    
    # Create group inputs
    group_inputs = group.nodes.new("NodeGroupInput")
    group_inputs.location = (-300, 0)
    for inp in inputs:
        if inp["type"] == "NodeSocketFloat":
            group.inputs.new("NodeSocketFloat", inp["name"])
        elif inp["type"] == "NodeSocketColor":
            group.inputs.new("NodeSocketColor", inp["name"])
        elif inp["type"] == "NodeSocketVector":
            group.inputs.new("NodeSocketVector", inp["name"])
    
    # Create group outputs
    group_outputs = group.nodes.new("NodeGroupOutput")
    group_outputs.location = (300, 0)
    for out in outputs:
        if out["type"] == "NodeSocketFloat":
            group.outputs.new("NodeSocketFloat", out["name"])
        elif out["type"] == "NodeSocketColor":
            group.outputs.new("NodeSocketColor", out["name"])
        elif out["type"] == "NodeSocketVector":
            group.outputs.new("NodeSocketVector", out["name"])
    
    # Let the caller populate internal nodes
    build_fn(group)
    
    return group


def build_palette_ramp_group(palette, contrast="medium"):
    """
    Creates a node group for palette color ramping.
    
    Args:
        palette: List of hex color strings
        contrast: Contrast level ("low", "medium", "high")
    
    Returns:
        Node group for palette ramping
    """
    def build_fn(group):
        nodes = group.nodes
        links = group.links
        
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (0, 0)
        
        # Assign palette colors
        max_ramp = min(4, len(palette)) if palette else 2
        for i, hex_color in enumerate(palette[:max_ramp]):
            col = hex_to_rgb(hex_color)
            col = adjust_contrast(col, contrast)
            
            if i == 0:
                elem = ramp.color_ramp.elements[0]
                elem.position = 0.0
            elif i == 1:
                elem = ramp.color_ramp.elements[1]
                elem.position = 1.0
            else:
                elem = ramp.color_ramp.elements.new(i / (max_ramp - 1))
            
            elem.color = (*col, 1.0)
        
        # Default colors if no palette
        if not palette:
            elem0 = ramp.color_ramp.elements[0]
            elem1 = ramp.color_ramp.elements[1]
            elem0.color = (0.2, 0.2, 0.25, 1)
            elem1.color = (0.6, 0.8, 0.6, 1)
        
        # Connect input → ramp → output
        links.new(nodes["Group Input"].outputs["Factor"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], nodes["Group Output"].inputs["Color"])
    
    return create_node_group(
        name="PaletteRampLayer",
        inputs=[{"name": "Factor", "type": "NodeSocketFloat"}],
        outputs=[{"name": "Color", "type": "NodeSocketColor"}],
        build_fn=build_fn
    )


def build_detail_noise_group():
    """
    Creates a node group for detail noise generation.
    
    Returns:
        Node group for detail noise
    """
    def build_fn(group):
        nodes = group.nodes
        links = group.links
        
        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (0, 0)
        
        mapping = nodes.new("ShaderNodeMapping")
        mapping.location = (-200, 0)
        
        tex_coord = nodes.new("ShaderNodeTexCoord")
        tex_coord.location = (-400, 0)
        
        # Connect inputs
        links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        # Connect scale and detail directly to noise
        links.new(nodes["Group Input"].outputs["Scale"], noise.inputs["Scale"])
        links.new(nodes["Group Input"].outputs["Detail"], noise.inputs["Detail"])
        
        # Connect output
        links.new(noise.outputs["Fac"], nodes["Group Output"].inputs["Mask"])
    
    return create_node_group(
        name="DetailNoiseLayer",
        inputs=[
            {"name": "Scale", "type": "NodeSocketFloat"},
            {"name": "Detail", "type": "NodeSocketFloat"}
        ],
        outputs=[
            {"name": "Mask", "type": "NodeSocketFloat"}
        ],
        build_fn=build_fn
    )


def build_base_noise_group():
    """
    Creates a node group for base noise generation.
    
    Returns:
        Node group for base noise
    """
    def build_fn(group):
        nodes = group.nodes
        links = group.links
        
        noise = nodes.new("ShaderNodeTexNoise")
        noise.location = (0, 0)
        
        mapping = nodes.new("ShaderNodeMapping")
        mapping.location = (-200, 0)
        
        tex_coord = nodes.new("ShaderNodeTexCoord")
        tex_coord.location = (-400, 0)
        
        # Connect inputs
        links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        # Connect scale and detail directly to noise
        links.new(nodes["Group Input"].outputs["Scale"], noise.inputs["Scale"])
        links.new(nodes["Group Input"].outputs["Detail"], noise.inputs["Detail"])
        
        # Connect output
        links.new(noise.outputs["Fac"], nodes["Group Output"].inputs["Fac"])
    
    return create_node_group(
        name="BaseNoiseLayer",
        inputs=[
            {"name": "Scale", "type": "NodeSocketFloat"},
            {"name": "Detail", "type": "NodeSocketFloat"}
        ],
        outputs=[
            {"name": "Fac", "type": "NodeSocketFloat"}
        ],
        build_fn=build_fn
    )


def build_voronoi_group():
    """
    Creates a node group for Voronoi pattern generation.
    
    Returns:
        Node group for Voronoi patterns
    """
    def build_fn(group):
        nodes = group.nodes
        links = group.links
        
        voronoi = nodes.new("ShaderNodeTexVoronoi")
        voronoi.location = (0, 0)
        
        mapping = nodes.new("ShaderNodeMapping")
        mapping.location = (-200, 0)
        
        tex_coord = nodes.new("ShaderNodeTexCoord")
        tex_coord.location = (-400, 0)
        
        # Connect inputs
        links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])
        # Connect scale directly to voronoi
        links.new(nodes["Group Input"].outputs["Scale"], voronoi.inputs["Scale"])
        
        # Connect output
        links.new(voronoi.outputs["Distance"], nodes["Group Output"].inputs["Distance"])
    
    return create_node_group(
        name="VoronoiLayer",
        inputs=[
            {"name": "Scale", "type": "NodeSocketFloat"}
        ],
        outputs=[
            {"name": "Distance", "type": "NodeSocketFloat"}
        ],
        build_fn=build_fn
    )


def build_rim_light_group():
    """
    Creates a node group for rim lighting effects.
    
    Returns:
        Node group for rim lighting
    """
    def build_fn(group):
        nodes = group.nodes
        links = group.links
        
        layer_weight = nodes.new("ShaderNodeLayerWeight")
        layer_weight.location = (-200, 0)
        
        mix = nodes.new("ShaderNodeMixRGB")
        mix.location = (0, 0)
        mix.blend_type = "ADD"
        
        # Connect inputs
        links.new(layer_weight.outputs["Facing"], mix.inputs["Fac"])
        links.new(nodes["Group Input"].outputs["BaseColor"], mix.inputs["Color1"])
        links.new(nodes["Group Input"].outputs["RimColor"], mix.inputs["Color2"])
        # Use strength to control mix factor
        links.new(nodes["Group Input"].outputs["Strength"], mix.inputs["Fac"])
        
        # Connect output
        links.new(mix.outputs["Color"], nodes["Group Output"].inputs["Color"])
    
    return create_node_group(
        name="RimLightLayer",
        inputs=[
            {"name": "BaseColor", "type": "NodeSocketColor"},
            {"name": "RimColor", "type": "NodeSocketColor"},
            {"name": "Strength", "type": "NodeSocketFloat"}
        ],
        outputs=[
            {"name": "Color", "type": "NodeSocketColor"}
        ],
        build_fn=build_fn
    )


def build_emission_group():
    """
    Creates a node group for emission/glow effects.
    
    Returns:
        Node group for emission
    """
    def build_fn(group):
        nodes = group.nodes
        links = group.links
        
        emission = nodes.new("ShaderNodeEmission")
        emission.location = (0, 0)
        
        # Connect inputs
        links.new(nodes["Group Input"].outputs["Color"], emission.inputs["Color"])
        links.new(nodes["Group Input"].outputs["Strength"], emission.inputs["Strength"])
        
        # Connect output
        links.new(emission.outputs["Emission"], nodes["Group Output"].inputs["Emission"])
    
    return create_node_group(
        name="EmissionLayer",
        inputs=[
            {"name": "Color", "type": "NodeSocketColor"},
            {"name": "Strength", "type": "NodeSocketFloat"}
        ],
        outputs=[
            {"name": "Emission", "type": "NodeSocketColor"}
        ],
        build_fn=build_fn
    )


# ------------------------------------------------------------
# Main entry: build material from visual block
# ------------------------------------------------------------

def apply_quality_settings(mat, quality):
    """
    Apply quality-based modifications to a material.
    quality: "draft", "standard", "high", "ultra"
    """
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    if quality == "draft":
        # Low detail, fast bake - reduce noise scales
        for node in nodes:
            if hasattr(node, "inputs"):
                if "Scale" in node.inputs:
                    node.inputs["Scale"].default_value *= 0.5
                if "Detail" in node.inputs:
                    node.inputs["Detail"].default_value = max(1.0, node.inputs["Detail"].default_value * 0.5)

    elif quality == "standard":
        # Default settings, no changes needed
        pass

    elif quality == "high":
        # Add detail noise layer
        principled = None
        for node in nodes:
            if node.type == "BSDF_PRINCIPLED":
                principled = node
                break

        if principled:
            # Find the base color input source
            base_color_input = principled.inputs["Base Color"]
            if base_color_input.is_linked:
                source_link = base_color_input.links[0]
                source_node = source_link.from_node
                
                # Disconnect existing link
                links.remove(source_link)
                
                # Add detail noise
                detail_noise = nodes.new("ShaderNodeTexNoise")
                detail_noise.location = (-200, 300)
                detail_noise.inputs["Scale"].default_value = 50.0
                detail_noise.inputs["Detail"].default_value = 10.0
                detail_noise.inputs["Roughness"].default_value = 0.5

                # Add mix node for detail
                detail_mix = nodes.new("ShaderNodeMixRGB")
                detail_mix.blend_type = "MULTIPLY"
                detail_mix.location = (0, 200)
                detail_mix.inputs["Fac"].default_value = 0.2  # Subtle detail

                # Connect detail noise
                tex_coord = None
                mapping = None
                for node in nodes:
                    if node.type == "TEX_COORD":
                        tex_coord = node
                    elif node.type == "MAPPING":
                        mapping = node

                if tex_coord and mapping:
                    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
                    links.new(mapping.outputs["Vector"], detail_noise.inputs["Vector"])

                # Mix detail with base color
                links.new(detail_noise.outputs["Fac"], detail_mix.inputs["Color1"])
                links.new(source_node.outputs["Color"], detail_mix.inputs["Color2"])
                links.new(detail_mix.outputs["Color"], principled.inputs["Base Color"])

    elif quality == "ultra":
        # Maximum detail - boost all detail values
        for node in nodes:
            if hasattr(node, "inputs"):
                if "Detail" in node.inputs:
                    node.inputs["Detail"].default_value = min(15.0, node.inputs["Detail"].default_value * 1.5)
                if "Roughness" in node.inputs:
                    node.inputs["Roughness"].default_value = min(1.0, node.inputs["Roughness"].default_value * 1.2)

        # Add micro-detail layer (similar to high, but more intense)
        principled = None
        for node in nodes:
            if node.type == "BSDF_PRINCIPLED":
                principled = node
                break

        if principled:
            base_color_input = principled.inputs["Base Color"]
            if base_color_input.is_linked:
                source_link = base_color_input.links[0]
                source_node = source_link.from_node
                
                # Disconnect existing link
                links.remove(source_link)
                
                # Micro-detail noise
                micro_noise = nodes.new("ShaderNodeTexNoise")
                micro_noise.location = (-200, 400)
                micro_noise.inputs["Scale"].default_value = 100.0
                micro_noise.inputs["Detail"].default_value = 15.0
                micro_noise.inputs["Roughness"].default_value = 0.3

                # Mix for micro-detail
                micro_mix = nodes.new("ShaderNodeMixRGB")
                micro_mix.blend_type = "OVERLAY"
                micro_mix.location = (0, 300)
                micro_mix.inputs["Fac"].default_value = 0.15

                tex_coord = None
                mapping = None
                for node in nodes:
                    if node.type == "TEX_COORD":
                        tex_coord = node
                    elif node.type == "MAPPING":
                        mapping = node

                if tex_coord and mapping:
                    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
                    links.new(mapping.outputs["Vector"], micro_noise.inputs["Vector"])

                links.new(micro_noise.outputs["Fac"], micro_mix.inputs["Color1"])
                links.new(source_node.outputs["Color"], micro_mix.inputs["Color2"])
                links.new(micro_mix.outputs["Color"], principled.inputs["Base Color"])


def build_material_from_visual_with_groups(visual, mat_name="GeneratedMaterial", quality="standard"):
    """
    Builds a material using node groups for manual tweaking (export mode).
    Each procedural layer becomes a reusable, editable node group.
    
    visual: dict with 'icon', 'fx', 'projectile' etc.
    quality: "draft", "standard", "high", "ultra"
    Returns: Blender Material with node groups.
    """
    icon_data = visual.get("icon", {})
    style = icon_data.get("style", "painterly")
    shape = icon_data.get("shape", "magical symbol")
    palette = icon_data.get("palette", [])
    contrast = icon_data.get("contrast", "medium")
    lighting = icon_data.get("lighting", "").lower()
    glow = icon_data.get("glow", False)
    
    shape_hints = get_shape_hints(shape)
    
    mat = bpy.data.materials.new(mat_name)
    clear_material_nodes(mat)
    
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Create output and principled nodes
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (800, 0)
    
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (600, 0)
    
    # Create node groups based on quality
    x_offset = -600
    y_offset = 0
    
    # Base noise layer (always present)
    base_noise_group = build_base_noise_group()
    base_noise_node = nodes.new("ShaderNodeGroup")
    base_noise_node.node_tree = base_noise_group
    base_noise_node.location = (x_offset, y_offset)
    base_noise_node.inputs["Scale"].default_value = shape_hints["noise_scale"]
    base_noise_node.inputs["Detail"].default_value = 5.0 if quality != "draft" else 2.0
    base_noise_node.label = "Base Noise"
    x_offset += 200
    
    # Voronoi layer (for pattern)
    voronoi_group = build_voronoi_group()
    voronoi_node = nodes.new("ShaderNodeGroup")
    voronoi_node.node_tree = voronoi_group
    voronoi_node.location = (x_offset, y_offset)
    voronoi_node.inputs["Scale"].default_value = shape_hints["voronoi_scale"]
    voronoi_node.label = "Voronoi Pattern"
    x_offset += 200
    
    # Mix base noise and voronoi
    mix_pattern = nodes.new("ShaderNodeMixRGB")
    mix_pattern.location = (x_offset, y_offset)
    mix_pattern.blend_type = "MIX"
    mix_pattern.inputs["Fac"].default_value = 0.4
    mix_pattern.label = "Pattern Mix"
    x_offset += 200
    
    # Palette ramp group
    palette_group = build_palette_ramp_group(palette, contrast)
    palette_node = nodes.new("ShaderNodeGroup")
    palette_node.node_tree = palette_group
    palette_node.location = (x_offset, y_offset)
    palette_node.label = "Palette Ramp"
    x_offset += 200
    
    # Connect base layers
    links.new(base_noise_node.outputs["Fac"], mix_pattern.inputs[1])
    links.new(voronoi_node.outputs["Distance"], mix_pattern.inputs[2])
    links.new(mix_pattern.outputs["Color"], palette_node.inputs["Factor"])
    
    # Quality-dependent layers
    if quality in ["high", "ultra"]:
        # Detail noise layer
        detail_noise_group = build_detail_noise_group()
        detail_noise_node = nodes.new("ShaderNodeGroup")
        detail_noise_node.node_tree = detail_noise_group
        detail_noise_node.location = (x_offset, y_offset - 200)
        detail_noise_node.inputs["Scale"].default_value = 50.0
        detail_noise_node.inputs["Detail"].default_value = 10.0 if quality == "high" else 15.0
        detail_noise_node.label = "Detail Noise"
        
        # Mix detail with palette
        detail_mix = nodes.new("ShaderNodeMixRGB")
        detail_mix.location = (x_offset + 200, y_offset - 200)
        detail_mix.blend_type = "MULTIPLY"
        detail_mix.inputs["Fac"].default_value = 0.2
        detail_mix.label = "Detail Mix"
        
        links.new(detail_noise_node.outputs["Mask"], detail_mix.inputs[1])
        links.new(palette_node.outputs["Color"], detail_mix.inputs[2])
        
        # Update palette output to detail mix
        palette_output = detail_mix.outputs["Color"]
    else:
        palette_output = palette_node.outputs["Color"]
    
    # Rim lighting (if specified)
    if "rim" in lighting or glow:
        rim_group = build_rim_light_group()
        rim_node = nodes.new("ShaderNodeGroup")
        rim_node.node_tree = rim_group
        rim_node.location = (x_offset + 200, y_offset)
        rim_node.inputs["BaseColor"].default_value = (0.0, 0.0, 0.0, 1.0)  # Will be connected
        rim_node.inputs["RimColor"].default_value = (1.0, 1.0, 1.0, 1.0)
        rim_node.inputs["Strength"].default_value = 0.7
        rim_node.label = "Rim Light"
        
        links.new(palette_output, rim_node.inputs["BaseColor"])
        links.new(rim_node.outputs["Color"], principled.inputs["Base Color"])
    else:
        links.new(palette_output, principled.inputs["Base Color"])
    
    # Emission (if glow is enabled)
    if glow:
        emission_group = build_emission_group()
        emission_node = nodes.new("ShaderNodeGroup")
        emission_node.node_tree = emission_group
        emission_node.location = (x_offset + 200, y_offset + 200)
        emission_node.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)  # Will use palette color
        emission_node.inputs["Strength"].default_value = 2.0
        emission_node.label = "Emission"
        
        links.new(palette_output, emission_node.inputs["Color"])
        links.new(emission_node.outputs["Emission"], principled.inputs["Emission"])
    
    # Set principled defaults
    principled.inputs["Roughness"].default_value = 0.6
    principled.inputs["Specular"].default_value = 0.2
    
    # Connect to output
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    
    return mat


def build_material_from_visual(visual, mat_name="GeneratedMaterial", quality="standard", export_node_groups=False):
    """
    visual: dict with 'icon', 'fx', 'projectile' etc.
    quality: "draft", "standard", "high", "ultra"
    export_node_groups: If True, use node groups for manual tweaking
    Returns: Blender Material.
    """
    if export_node_groups:
        return build_material_from_visual_with_groups(visual, mat_name, quality)
    
    # Original flat node tree approach
    icon_data = visual.get("icon", {})
    style = icon_data.get("style", "painterly")

    mat = bpy.data.materials.new(mat_name)
    clear_material_nodes(mat)

    if style == "pixel":
        build_pixel_material(mat, icon_data)
    elif style == "flat":
        build_flat_material(mat, icon_data)
    else:
        # Default to painterly if unknown
        build_painterly_material(mat, icon_data)

    # Apply quality settings
    apply_quality_settings(mat, quality)

    return mat


# ------------------------------------------------------------
# Optional CLI wrapper for testing
# ------------------------------------------------------------

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    # Simple: expect a single JSON string via --visualJson
    visual_json = None
    for i, tok in enumerate(argv):
        if tok == "--visualJson" and i + 1 < len(argv):
            visual_json = argv[i + 1]
            break
    return visual_json


def main():
    visual_json = parse_args()
    if not visual_json:
        print("No --visualJson provided; skipping.")
        return

    visual = json.loads(visual_json)
    mat = build_material_from_visual(visual, mat_name="TestMaterial")
    print(f"Material '{mat.name}' created from visual block.")


if __name__ == "__main__":
    main()

