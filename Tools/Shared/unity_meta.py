#!/usr/bin/env python3
"""
Shared Unity .meta writer for AAMT (Elin / Qud / others).

Deterministic GUID from relative path so re-runs stay stable. Supports
texture (default / sprite / normal / gui) and ModelImporter (FBX/OBJ)
settings without requiring the Editor.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Literal, Optional

TextureKind = Literal["default", "sprite", "normal", "gui"]


def deterministic_guid(asset_path: Path, root: Optional[Path] = None) -> str:
    """32-char hex GUID derived from path (stable across regenerations)."""
    p = asset_path.resolve()
    key = str(p.relative_to(root.resolve())) if root else str(p)
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def write_texture_meta(
    texture_path: Path | str,
    *,
    kind: TextureKind = "default",
    max_size: int = 2048,
    generate_mipmaps: bool = True,
    srgb: bool = True,
    wrap_mode: int = 1,  # 0 clamp, 1 repeat
    filter_mode: int = 1,  # 0 point, 1 bilinear
    overwrite: bool = False,
    root_for_guid: Optional[Path] = None,
) -> Path:
    """
    Write Unity TextureImporter .meta beside the PNG.
    kind=sprite → Sprite (2D and UI); kind=gui → same with mipmaps off.
    """
    texture_path = Path(texture_path)
    meta_path = Path(str(texture_path) + ".meta")
    if meta_path.exists() and not overwrite:
        return meta_path

    guid = deterministic_guid(texture_path, root_for_guid)
    mtime = int(time.time())

    if kind in ("sprite", "gui"):
        texture_type = 8  # Sprite
        sprite_mode = 1
        alpha_is_transparency = 1
        mipmaps = 0 if kind == "gui" else (1 if generate_mipmaps else 0)
        n_pot = 0
    elif kind == "normal":
        texture_type = 1  # NormalMap
        sprite_mode = 0
        alpha_is_transparency = 0
        mipmaps = 1 if generate_mipmaps else 0
        n_pot = 1
        srgb = False
    else:
        texture_type = 0  # Default
        sprite_mode = 0
        alpha_is_transparency = 0
        mipmaps = 1 if generate_mipmaps else 0
        n_pot = 1

    # Simplified but Unity-readable TextureImporter block (matches Elin generator style).
    content = f"""fileFormatVersion: 2
guid: {guid}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 12
  mipmaps:
    mipMapMode: 0
    enableMipMap: {mipmaps}
    sRGBTexture: {1 if srgb else 0}
    linearTexture: {0 if srgb else 1}
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: {max_size}
  textureSettings:
    serializedVersion: 2
    filterMode: {filter_mode}
    aniso: 1
    mipBias: 0
    wrapU: {wrap_mode}
    wrapV: {wrap_mode}
    wrapW: {wrap_mode}
  nPOTScale: {n_pot}
  lightmap: 0
  compressionQuality: 50
  spriteMode: {sprite_mode}
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.5}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 1
  alphaUsage: 1
  alphaIsTransparency: {alpha_is_transparency}
  spriteTessellationDetail: -1
  textureType: {texture_type}
  textureShape: 1
  singleChannelComponent: 0
  flipbookRows: 1
  flipbookColumns: 1
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureFormatSet: 0
  ignorePngGamma: 0
  applyGammaDecoding: 0
  platformSettings:
  - serializedVersion: 3
    buildTarget: DefaultTexturePlatform
    maxTextureSize: {max_size}
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 1
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    physicsShape: []
  mipmapLimitGroupName: 
  pSDRemoveMatte: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""
    meta_path.write_text(content, encoding="utf-8")
    # Touch unused mtime to silence linters about unused var in some checkers
    _ = mtime
    return meta_path


def write_default_meta(asset_path: Path | str, *, overwrite: bool = False) -> Path:
    asset_path = Path(asset_path)
    meta_path = Path(str(asset_path) + ".meta")
    if meta_path.exists() and not overwrite:
        return meta_path
    guid = deterministic_guid(asset_path)
    meta_path.write_text(
        f"fileFormatVersion: 2\nguid: {guid}\nDefaultImporter:\n  externalObjects: {{}}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n",
        encoding="utf-8",
    )
    return meta_path


def write_model_meta(
    model_path: Path | str,
    *,
    overwrite: bool = False,
    root_for_guid: Optional[Path] = None,
    scale_factor: float = 1.0,
    generate_colliders: bool = False,
    import_animation: bool = False,
) -> Path:
    """
    Write a Unity ModelImporter .meta for FBX/OBJ (readable by Editor + AssetBundles).
    Prefer this over write_default_meta for mesh assets.
    """
    model_path = Path(model_path)
    meta_path = Path(str(model_path) + ".meta")
    if meta_path.exists() and not overwrite:
        return meta_path

    guid = deterministic_guid(model_path, root_for_guid)
    colliders = 1 if generate_colliders else 0
    anim = 1 if import_animation else 0
    content = f"""fileFormatVersion: 2
guid: {guid}
ModelImporter:
  serializedVersion: 21300
  internalIDToNameTable: []
  externalObjects: {{}}
  materials:
    materialImportMode: 1
    materialName: 0
    materialSearch: 1
    materialLocation: 1
  animations:
    legacyGenerateAnimations: 4
    bakeSimulation: 0
    resampleCurves: 1
    optimizeGameObjects: 0
    motionNodeName: 
    animationImportErrors: 
    animationImportWarnings: 
    animationRetargetingWarnings: 
    animationDoRetargetingWarnings: 0
    importAnimatedCustomProperties: 0
    importConstraints: 0
    animationCompression: 1
    animationRotationError: 0.5
    animationPositionError: 0.5
    animationScaleError: 0.5
    animationWrapMode: 0
    extraExposedTransformPaths: []
    extraUserProperties: []
    clipAnimations: []
    isGenerationTemporary: 0
  meshes:
    lODScreenPercentages: []
    globalScale: {scale_factor}
    meshCompression: 0
    addColliders: {colliders}
    useSRGBMaterialColor: 1
    sortHierarchyByName: 1
    importVisibility: 1
    importBlendShapes: 1
    importCameras: 0
    importLights: 0
    fileIdsGeneration: 2
    swapUVChannels: 0
    generateSecondaryUV: 0
    useFileUnits: 1
    keepQuads: 0
    weldVertices: 1
    bakeAxisConversion: 0
    preserveHierarchy: 0
    skinWeightsMode: 0
    maxBonesPerVertex: 4
    minBoneWeight: 0.001
    optimizeBones: 1
    meshOptimizationFlags: -1
    autoGenerateAvatarMap: 0
  tangents:
    normalImportMode: 0
    tangentImportMode: 3
  importedTakeInfos: []
  importAnimation: {anim}
  humanDescription:
    serializedVersion: 3
    human: []
    skeleton: []
    armTwist: 0.5
    foreArmTwist: 0.5
    upperLegTwist: 0.5
    legTwist: 0.5
    armStretch: 0.05
    legStretch: 0.05
    feetSpacing: 0
    globalScale: {scale_factor}
    rootMotionBoneName: 
    hasTranslationDoF: 0
    hasExtraRoot: 0
    skeletonHasParents: 1
  lastHumanDescriptionAvatarSource: {{instanceID: 0}}
  autoGenerateAvatarMappingIfUnspecified: 1
  animationType: 0
  humanoidOversampling: 1
  avatarSetup: 0
  addHumanoidExtraRootOnlyWhenUsingAvatar: 1
  additionalBone: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""
    meta_path.write_text(content, encoding="utf-8")
    return meta_path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Write Unity .meta for a texture or model")
    ap.add_argument("path", help="PNG / FBX / OBJ path")
    ap.add_argument("--kind", choices=["default", "sprite", "normal", "gui", "model"], default="default")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    p = Path(args.path)
    if args.kind == "model" or p.suffix.lower() in (".fbx", ".obj", ".dae"):
        out = write_model_meta(p, overwrite=args.overwrite)
    else:
        out = write_texture_meta(p, kind=args.kind if args.kind != "model" else "default", overwrite=args.overwrite)
    print(f"[OK] {out}")
