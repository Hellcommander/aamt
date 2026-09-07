from pathlib import Path
import py_compile

path = Path(r"E:\tools\sd3.5\sd3.5\server.py")
text = path.read_text(encoding="utf-8")
if 'def _plan_inference_dims' in text and 'SERVER_VERSION = "2.2"' in text:
    print("already patched")
    raise SystemExit(0)

# --- docstring / version ---
old = '''  - Custom resolution support for game tools: request width/height (or size="WxH")
    at the final asset size. Default min is 32 so pixel/sprite pipelines can
    generate native frames without client-side crush-downscaling.
'''
new = '''  - Custom resolution support for game tools: request width/height (or size="WxH")
    as the *delivery* size. Low-res requests mirror ToME\'s sd_http_client planner:
    infer at max(SD_QUALITY_FLOOR, delivery * supersample) snapped to SD_DIM_STEP
    (icons: floor 512, supersample 1.5, 24 steps), then stepwise Lanczos-halve
    down to delivery with ToME sharpen/contrast (1.1 / 1.05). Opt out with
    SD_NATIVE_RESOLUTION=1 or JSON {"native": true}.
'''
if old not in text:
    raise SystemExit("doc block missing")
text = text.replace(old, new, 1)

old_env = '''  SD_MIN_DIM / SD_MAX_DIM   dimension clamps                     (default 32 / 1536)
  SD_DIM_STEP             snap grid (VAE-friendly)               (default 16)
  SD_MAX_STEPS          max inference steps                      (default 100)
  SD_ALLOW_NONADMIN     1 to skip Windows admin gate
'''
new_env = '''  SD_MIN_DIM / SD_MAX_DIM   delivery dimension clamps            (default 32 / 1536)
  SD_DIM_STEP             snap grid (VAE-friendly)               (default 16)
  SD_QUALITY_FLOOR        min short side for *inference*         (default 512)
  SD_SUPER_SAMPLE         max upscale over delivery (ToME icon)  (default 1.5)
  SD_NATIVE_RESOLUTION    1 = skip floor upscale (true native)   (default 0)
  SD_DOWNSCALE_SHARPNESS  post-Lanczos sharpen (ToME default)    (default 1.1)
  SD_DOWNSCALE_CONTRAST   post-Lanczos contrast (ToME default)   (default 1.05)
  SD_ICON_STEPS           default steps when delivery < floor    (default 24)
  SD_MAX_STEPS          max inference steps                      (default 100)
  SD_ALLOW_NONADMIN     1 to skip Windows admin gate
'''
if old_env not in text:
    raise SystemExit("env block missing")
text = text.replace(old_env, new_env, 1)
text = text.replace('SERVER_VERSION = "2.1"', 'SERVER_VERSION = "2.2"', 1)

helpers = r'''def _resolve_request_dims(request_data: dict):
    """Resolve delivery width/height from width/height, size, or resolution fields."""
    alias_w, alias_h = _parse_size_field(request_data)
    raw_w = request_data.get("width", alias_w if alias_w is not None else 1024)
    raw_h = request_data.get("height", alias_h if alias_h is not None else 1024)
    width = _snap_dim(raw_w, 1024)
    height = _snap_dim(raw_h, 1024)
    return width, height, raw_w, raw_h


def _quality_floor() -> int:
    """SD3.5 Medium quality floor for the short inference side (default 512)."""
    _, hi, step = _dim_bounds()
    floor = max(step, _env_int("SD_QUALITY_FLOOR", 512))
    return min(floor, hi)


def _super_sample() -> float:
    """Max upscale over delivery size (ToME icon profile default 1.5)."""
    try:
        return max(1.0, float(os.environ.get("SD_SUPER_SAMPLE", "1.5") or "1.5"))
    except ValueError:
        return 1.5


def _want_native_resolution(request_data: dict) -> bool:
    """True when caller opts into real tiny inference (no quality-floor upscale)."""
    if _env_bool("SD_NATIVE_RESOLUTION", False):
        return True
    for key in ("native", "native_resolution", "nativeResolution"):
        if key not in request_data:
            continue
        val = request_data.get(key)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in ("1", "true", "yes", "on")
    return False


def _snap_up(value: float, step: int, lo: int, hi: int) -> int:
    v = int(round(float(value) / float(step))) * step
    v = max(lo, min(hi, v))
    return max(lo, min(hi, int(round(v / float(step))) * step))


def _plan_inference_dims(delivery_w: int, delivery_h: int, *, native: bool = False):
    """
    Mirror Tools/Shared/sd_http_client.plan_sd_size for icon/delivery targets:

      gen = delivery * SD_SUPER_SAMPLE (default 1.5)
      if short side < SD_QUALITY_FLOOR (default 512): scale up so short == floor
      snap to SD_DIM_STEP; cap aspect at ~2:1; clamp to SD_MAX_DIM

    Returns (gen_w, gen_h, upscaled: bool).
    """
    lo, hi, step = _dim_bounds()
    dw = max(lo, min(hi, int(delivery_w)))
    dh = max(lo, min(hi, int(delivery_h)))
    if native:
        return dw, dh, False

    floor = _quality_floor()
    ss = _super_sample()
    w = float(dw) * ss
    h = float(dh) * ss
    short = min(w, h)
    if short < float(floor):
        factor = float(floor) / short
        w *= factor
        h *= factor

    # Cap extreme aspects (~2:1) like the ToME client planner
    short, longest = min(w, h), max(w, h)
    if longest > short * 2.0:
        if w >= h:
            w = short * 2.0
        else:
            h = short * 2.0

    gen_w = _snap_up(w, step, lo, hi)
    gen_h = _snap_up(h, step, lo, hi)
    # Keep short side at least floor after snap when delivery was below floor
    if min(dw, dh) < floor and min(gen_w, gen_h) < floor:
        if gen_w <= gen_h:
            gen_w = _snap_up(floor, step, floor, hi)
            gen_h = _snap_up(gen_w * (dh / float(dw)), step, lo, hi)
        else:
            gen_h = _snap_up(floor, step, floor, hi)
            gen_w = _snap_up(gen_h * (dw / float(dh)), step, lo, hi)

    upscaled = (gen_w, gen_h) != (dw, dh)
    return gen_w, gen_h, upscaled


def _default_steps_for_delivery(delivery_w: int, delivery_h: int, requested_steps) -> int:
    """
    When delivery is below the quality floor and the client omitted a strong
    steps preference, use ToME icon default (24). Explicit client steps win.
    """
    floor = _quality_floor()
    icon_steps = _env_int("SD_ICON_STEPS", 24)
    # If client sent steps explicitly and it is not the server default 28, keep it.
    if requested_steps is not None:
        try:
            rs = int(requested_steps)
            if rs > 0:
                # Treat missing/defaulty 28 from older clients on tiny icons as icon path
                if min(delivery_w, delivery_h) < floor and rs == 28:
                    return _clamp_steps(icon_steps)
                return _clamp_steps(rs)
        except (TypeError, ValueError):
            pass
    if min(delivery_w, delivery_h) < floor:
        return _clamp_steps(icon_steps)
    return _clamp_steps(28)


def _lanczos_resample():
    from PIL import Image
    return getattr(Image, "Resampling", Image).LANCZOS


def _downscale_image_tome(image, delivery_w: int, delivery_h: int):
    """
    Detail-preserving downscale matching ToME (tome_sd_pipeline):

      1) stepwise Lanczos (halve while >2x target) — scaling-steps method
      2) final Lanczos to exact delivery size
      3) Sharpness 1.1 + Contrast 1.05
    """
    if image.size == (delivery_w, delivery_h):
        return image

    from PIL import ImageEnhance

    resample = _lanczos_resample()
    img = image
    target_short = max(1, min(delivery_w, delivery_h))
    steps_done = 0
    while min(img.size) > target_short * 2:
        nw = max(delivery_w, img.size[0] // 2)
        nh = max(delivery_h, img.size[1] // 2)
        if (nw, nh) == img.size:
            break
        img = img.resize((nw, nh), resample)
        steps_done += 1

    if img.size != (delivery_w, delivery_h):
        img = img.resize((delivery_w, delivery_h), resample)
        steps_done += 1

    try:
        sharp = float(os.environ.get("SD_DOWNSCALE_SHARPNESS", "1.1") or "1.1")
    except ValueError:
        sharp = 1.1
    try:
        contrast = float(os.environ.get("SD_DOWNSCALE_CONTRAST", "1.05") or "1.05")
    except ValueError:
        contrast = 1.05
    if abs(sharp - 1.0) > 1e-6:
        img = ImageEnhance.Sharpness(img).enhance(sharp)
    if abs(contrast - 1.0) > 1e-6:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if steps_done:
        _log(
            f"Downscale steps: {image.size[0]}x{image.size[1]} -> "
            f"{delivery_w}x{delivery_h} ({steps_done} Lanczos step(s), "
            f"sharp={sharp}, contrast={contrast})"
        )
    return img


def _clamp_steps(value) -> int:
'''

start = 'def _resolve_request_dims(request_data: dict):\n    """Resolve width/height from width/height, size, or resolution fields."""'
end = 'def _clamp_steps(value) -> int:'
if start not in text:
    # maybe already delivery docstring
    start = 'def _resolve_request_dims(request_data: dict):\n    """Resolve delivery width/height from width/height, size, or resolution fields."""'
if start not in text:
    raise SystemExit("resolve_request_dims not found")
i0 = text.index(start)
i1 = text.index(end, i0)
text = text[:i0] + helpers + text[i1 + len(end):]

old_h = '''            negative_prompt = (request_data.get("negative_prompt") or "").strip()
            width, height, raw_w, raw_h = _resolve_request_dims(request_data)
            steps = _clamp_steps(request_data.get("steps", 28))
            guidance_scale = _clamp_guidance(request_data.get("guidance_scale", 7.0))
            num_outputs = max(1, min(4, int(request_data.get("n", 1) or 1)))
            seed = _resolve_seed(request_data.get("seed"))
            lo, hi, step = _dim_bounds()

            if str(raw_w) != str(width) or str(raw_h) != str(height):
                _log(f"Resolution snapped: requested {raw_w}x{raw_h} -> {width}x{height} (step={step}, clamp={lo}-{hi})")
            _log(
                f"Request: {width}x{height} steps={steps} cfg={guidance_scale} "
                f"n={num_outputs} seed={seed} neg={'yes' if negative_prompt else 'no'}"
            )
            _log(f"  prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

            t0 = time.monotonic()
            images, seeds_used = generate_images(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                guidance_scale=guidance_scale,
                seed=seed,
                num_outputs=num_outputs,
            )
            elapsed = time.monotonic() - t0

            response_data = {
                "data": [],
                "seeds": seeds_used,
                "offload": offload_mode,
                "width": width,
                "height": height,
                "size": f"{width}x{height}",
                "resolution": {"width": width, "height": height, "step": step, "min": lo, "max": hi},
            }
            for img in images:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                response_data["data"].append({
                    "b64_json": base64.b64encode(buffered.getvalue()).decode(),
                    "url": None,
                    "width": width,
                    "height": height,
                })

            self._send_json(200, response_data)
            _log(f"OK: {len(images)} image(s) in {elapsed:.1f}s (offload={offload_mode})")'''

new_h = '''            negative_prompt = (request_data.get("negative_prompt") or "").strip()
            delivery_w, delivery_h, raw_w, raw_h = _resolve_request_dims(request_data)
            native = _want_native_resolution(request_data)
            gen_w, gen_h, upscaled = _plan_inference_dims(
                delivery_w, delivery_h, native=native
            )
            # ToME icon path: 512@24 for 64px delivery; scale infer size from final res
            steps = _default_steps_for_delivery(
                delivery_w, delivery_h, request_data.get("steps")
            )
            guidance_scale = _clamp_guidance(request_data.get("guidance_scale", 7.0))
            num_outputs = max(1, min(4, int(request_data.get("n", 1) or 1)))
            seed = _resolve_seed(request_data.get("seed"))
            lo, hi, step = _dim_bounds()
            floor = _quality_floor()

            if str(raw_w) != str(delivery_w) or str(raw_h) != str(delivery_h):
                _log(
                    f"Delivery snapped: requested {raw_w}x{raw_h} -> "
                    f"{delivery_w}x{delivery_h} (step={step}, clamp={lo}-{hi})"
                )
            if upscaled:
                _log(
                    f"ToME-style plan: delivery {delivery_w}x{delivery_h} -> "
                    f"infer {gen_w}x{gen_h} @ {steps} steps "
                    f"(floor={floor}, supersample={_super_sample()}), "
                    f"then stepwise Lanczos to delivery"
                )
            elif native and min(delivery_w, delivery_h) < floor:
                _log(
                    f"Native low-res: infer {gen_w}x{gen_h} "
                    f"(below floor {floor}; stall/quality risk)"
                )
            _log(
                f"Request: delivery={delivery_w}x{delivery_h} infer={gen_w}x{gen_h} "
                f"steps={steps} cfg={guidance_scale} n={num_outputs} seed={seed} "
                f"neg={'yes' if negative_prompt else 'no'}"
            )
            _log(f"  prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

            t0 = time.monotonic()
            images, seeds_used = generate_images(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=gen_w,
                height=gen_h,
                steps=steps,
                guidance_scale=guidance_scale,
                seed=seed,
                num_outputs=num_outputs,
            )
            if upscaled or (gen_w, gen_h) != (delivery_w, delivery_h):
                images = [
                    _downscale_image_tome(img, delivery_w, delivery_h) for img in images
                ]
            elapsed = time.monotonic() - t0

            response_data = {
                "data": [],
                "seeds": seeds_used,
                "offload": offload_mode,
                "width": delivery_w,
                "height": delivery_h,
                "size": f"{delivery_w}x{delivery_h}",
                "resolution": {
                    "width": delivery_w,
                    "height": delivery_h,
                    "inference_width": gen_w,
                    "inference_height": gen_h,
                    "upscaled": upscaled,
                    "native": native,
                    "quality_floor": floor,
                    "supersample": _super_sample(),
                    "downscale": "lanczos_stepwise+tome_sharpen",
                    "steps": steps,
                    "step": step,
                    "min": lo,
                    "max": hi,
                },
            }
            for img in images:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                response_data["data"].append({
                    "b64_json": base64.b64encode(buffered.getvalue()).decode(),
                    "url": None,
                    "width": delivery_w,
                    "height": delivery_h,
                })

            self._send_json(200, response_data)
            _log(
                f"OK: {len(images)} image(s) in {elapsed:.1f}s "
                f"(offload={offload_mode}, delivered {delivery_w}x{delivery_h})"
            )'''

if old_h not in text:
    raise SystemExit("handler block missing")
text = text.replace(old_h, new_h, 1)

old_ping = '''                "resolution": {
                    "min": lo,
                    "max": hi,
                    "step": step,
                    "accepts": ["width", "height", "size", "resolution"],
                    "example": {"width": 64, "height": 64, "size": "64x64"},
                },'''
new_ping = '''                "resolution": {
                    "min": lo,
                    "max": hi,
                    "step": step,
                    "quality_floor": _quality_floor(),
                    "supersample": _super_sample(),
                    "icon_steps": _env_int("SD_ICON_STEPS", 24),
                    "native_default": _env_bool("SD_NATIVE_RESOLUTION", False),
                    "low_res_workaround": (
                        "ToME plan_sd_size mirror: infer max(floor, delivery*ss) "
                        "then stepwise Lanczos + sharpen/contrast; native=true to skip"
                    ),
                    "accepts": ["width", "height", "size", "resolution", "native"],
                    "example": {"width": 64, "height": 64, "size": "64x64"},
                },'''
if old_ping not in text:
    raise SystemExit("ping block missing")
text = text.replace(old_ping, new_ping, 1)

if text.count("def _clamp_steps(value) -> int:") != 1:
    raise SystemExit("clamp_steps count wrong")

path.write_text(text, encoding="utf-8")
py_compile.compile(str(path), doraise=True)
print("OK patched", path, "v2.2")
