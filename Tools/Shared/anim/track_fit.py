"""Video -> skeletal animation: CoTracker3 follows the rigged mesh's visible vertices through a generated clip, then
per-frame joint rotations (and a root offset) are fitted so the skinned vertices land on those tracks through the
render camera. Then the clip is shaped for a game: retimed to 30 fps, looped or trimmed, kept in place.
Runs in the animation venv; anim_client.fit_motions drives it.

    python track_fit.py --work <dir> --video <clip.mp4> --clip <name> --kind loop|move|oneshot|death [--seconds S]

<dir> holds what blender_anim.py made (mesh.npz, rig.npz, cam.json, visible.npy). Writes <dir>/clips/<name>.npz
(fps, rot (F,J,4) wxyz, trans (F,3); see blender_anim.py) and <dir>/fit/<name>.json (errors, what was cut).
"""
import argparse, json, math, os, sys, time
from pathlib import Path

import numpy as np
import torch

LOCAL = Path(os.environ.get("HF_HOME") or r"D:\hf-cache") / "local"
COTRACKER = os.environ.get("AAMT_COTRACKER_CKPT") or str(LOCAL / "cotracker3" / "scaled_offline.pth")
dev = "cuda" if torch.cuda.is_available() else "cpu"


# ---- inputs ---------------------------------------------------------------------------------------------------------

def load_work(work):
    m = np.load(work / "mesh.npz")
    r = np.load(work / "rig.npz", allow_pickle=True)
    cam = json.loads((work / "cam.json").read_text())
    return dict(V=m["verts"].astype(np.float32), F=m["faces"], J=r["joints"].astype(np.float32), par=r["parents"].astype(int),
                W=r["weights"].astype(np.float32), names=[str(n) for n in r["names"]], P=np.array(cam["P"], np.float32),
                w=int(cam["width"]), h=int(cam["height"]), vis=np.load(work / "visible.npy"))


def project(P, X):
    x = X @ P[:, :3].T + P[:, 3]
    return x[..., :2] / x[..., 2:3].clamp(min=1e-4) if torch.is_tensor(x) else x[..., :2] / np.maximum(x[..., 2:3], 1e-4)


def read_video(path, w, h):
    import imageio.v3 as iio
    from PIL import Image
    frames = [np.asarray(Image.fromarray(f).convert("RGB").resize((w, h), Image.LANCZOS)) for f in iio.imiter(path)]
    return np.stack(frames)  # T,H,W,3 uint8


def pick_queries(d, k=1400):
    """Visible vertices spread over the frame and over every bone that has any: farthest-point in 3D, seeded so
    each bone gets a few of its own vertices first."""
    vis = np.nonzero(d["vis"])[0]
    V, W = d["V"], d["W"]
    pix = project(d["P"], V[vis])
    inside = (pix[:, 0] > 2) & (pix[:, 0] < d["w"] - 2) & (pix[:, 1] > 2) & (pix[:, 1] < d["h"] - 2)
    vis = vis[inside]
    rng = np.random.default_rng(0)
    owner = W[vis].argmax(1)
    chosen = []
    for j in range(W.shape[1]):
        mine = vis[owner == j]
        if len(mine):
            chosen.extend(rng.choice(mine, size=min(6, len(mine)), replace=False).tolist())
    chosen = list(dict.fromkeys(chosen))
    pts = V[vis]
    dist = np.full(len(vis), np.inf)
    for c in chosen:
        dist = np.minimum(dist, np.linalg.norm(pts - V[c], axis=1))
    while len(chosen) < min(k, len(vis)):
        i = int(dist.argmax())
        chosen.append(int(vis[i]))
        dist = np.minimum(dist, np.linalg.norm(pts - pts[i], axis=1))
    return np.array(chosen)


def track(video, q_pix):
    from cotracker.predictor import CoTrackerPredictor
    model = CoTrackerPredictor(checkpoint=COTRACKER, offline=True, window_len=60).to(dev).eval()
    v = torch.from_numpy(video).permute(0, 3, 1, 2)[None].float().to(dev)
    q = torch.cat([torch.zeros(len(q_pix), 1), torch.from_numpy(q_pix).float()], 1)[None].to(dev)
    # in chunks of queries: all of them through the whole clip at once filled the (shared) 11 GB card, and swapping
    # turned a three-minute track into twenty. fp32 throughout: the model carries pixel coordinates
    trs, vis = [], []
    with torch.no_grad():
        for i in range(0, q.shape[1], 500):
            tr, vi = model(v, queries=q[:, i:i + 500])
            trs.append(tr[0].float().cpu())
            vis.append(vi[0].float().cpu())
    del model, v
    torch.cuda.empty_cache()
    return torch.cat(trs, 1).numpy(), torch.cat(vis, 1).numpy().astype(np.float32)  # T,K,2 / T,K


# ---- the skinned forward model --------------------------------------------------------------------------------------

def rot6d(x):
    a, b = x[..., :3], x[..., 3:]
    a = torch.nn.functional.normalize(a, dim=-1)
    b = torch.nn.functional.normalize(b - (a * b).sum(-1, keepdim=True) * a, dim=-1)
    return torch.stack([a, b, torch.cross(a, b, dim=-1)], -1)  # columns


class Skin:
    def __init__(self, d):
        self.J = torch.from_numpy(d["J"]).to(dev)
        self.par = d["par"]
        self.order = []  # parents before children
        seen = set()
        while len(self.order) < len(self.par):
            for j, p in enumerate(self.par):
                if j not in seen and (p < 0 or p in seen):
                    self.order.append(j)
                    seen.add(j)

    def transforms(self, R, t):
        """R (T,J,3,3) parent-relative rotations about each joint, t (T,3) root offset -> world (T,J,3,3), (T,J,3)
        with D_j(x) = A_j x + b_j."""
        T_, nj = R.shape[:2]
        A = [None] * nj
        b = [None] * nj
        for j in self.order:
            p = self.par[j]
            pj = self.J[j]
            if p < 0:
                A[j] = R[:, j]
                b[j] = t + pj - (R[:, j] @ pj)
            else:
                A[j] = A[p] @ R[:, j]
                b[j] = torch.einsum("tab,tb->ta", A[p], pj - R[:, j] @ pj) + b[p]
        return torch.stack(A, 1), torch.stack(b, 1)

    def skin(self, A, b, X, W):
        """X (N,3) rest points, W (N,J) -> (T,N,3)."""
        Xw = torch.einsum("tjab,nb->tnja", A, X) + b[:, None]
        return (Xw * W[None, :, :, None]).sum(2)


# ---- fitting --------------------------------------------------------------------------------------------------------

def fit(d, qidx, tracks, tvis, iters=1600, grounded=True):
    sk = Skin(d)
    T_, nj = tracks.shape[0], len(d["par"])
    X = torch.from_numpy(d["V"][qidx]).to(dev)
    Wq = torch.from_numpy(d["W"][qidx]).to(dev)
    Wq = Wq / Wq.sum(1, keepdim=True).clamp(min=1e-6)
    P = torch.from_numpy(d["P"]).to(dev)
    trk = torch.from_numpy(tracks).to(dev)
    vis = torch.from_numpy(tvis).to(dev)
    # trust a track less where it disagrees with where frame 0 put the vertex (the video redrew the creature)
    p0 = project(P, X)
    start_err = (trk[0] - p0).norm(dim=-1)
    # CoTracker calls a lot "occluded" mid-clip whose tracks are still sensible: count them, lightly (Huber keeps
    # the wild ones from pulling hard)
    vis = (0.3 + 0.7 * vis) * (start_err < 0.03 * d["h"]).float()[None]
    pick = np.random.default_rng(1).choice(len(d["V"]), min(2500, len(d["V"])), replace=False)
    floor_pts, floor_W = torch.from_numpy(d["V"][pick]).to(dev), torch.from_numpy(d["W"][pick]).to(dev)
    # what touches the floor at rest (soles, leg tips): while it's down it shouldn't slide, so moving the body over
    # planted feet has to bend the legs, as in the video, instead of swinging them whole
    zr = d["V"][:, 2]
    low = np.nonzero(zr < zr.min() + 0.03 * np.ptp(zr))[0]
    low = low[np.random.default_rng(2).choice(len(low), min(400, len(low)), replace=False)] if len(low) else low
    foot_X, foot_W = torch.from_numpy(d["V"][low]).to(dev), torch.from_numpy(d["W"][low]).to(dev)
    # how much each joint is seen: joints nobody tracks lean harder on the rest pose
    seen = (Wq * vis.mean(0)[:, None]).sum(0)
    prior_w = 1.0 / (0.05 + seen / seen.max().clamp(min=1e-6))
    ident = torch.tensor([1., 0, 0, 0, 1, 0], device=dev)
    r6 = ident.repeat(T_, nj, 1).clone().requires_grad_(True)
    tr = torch.zeros(T_, 3, device=dev, requires_grad=True)
    roots = torch.tensor([bool(p < 0) for p in sk.par], device=dev)
    eye = torch.eye(3, device=dev)
    # weights, in units of "pixels of track error" so they read the same at any resolution (frame height 480 here)
    px = d["h"] / 480.0
    W_PRIOR, W_ACC, W_TACC, W_ANCHOR, W_FLOOR, W_SKATE = 0.3, 400.0, 4000.0, 1000.0, 20000.0, 30000.0

    def run(params, n, stage, lr):
        opt = torch.optim.Adam(params, lr=lr)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, n, lr * 0.1)
        for it in range(n):
            R = rot6d(r6)
            if stage == 0:  # whole-body first: only the roots move
                R = torch.where(roots[None, :, None, None], R, eye.expand_as(R))
            A, b = sk.transforms(R, tr)
            uv = project(P, sk.skin(A, b, X, Wq))
            err = (uv - trk).norm(dim=-1) / px
            data = (torch.where(err < 3, 0.5 * err ** 2 / 3, err - 1.5) * vis).sum() / vis.sum().clamp(min=1)
            prior = ((R - eye).pow(2).sum((-1, -2)) * prior_w[None]).mean()
            acc = (r6[2:] - 2 * r6[1:-1] + r6[:-2]).pow(2).sum(-1).mean()
            tacc = (tr[2:] - 2 * tr[1:-1] + tr[:-2]).pow(2).sum(-1).mean()
            anchor = (r6[0] - ident).pow(2).sum(-1).mean() + tr[0].pow(2).sum()
            loss = data + W_PRIOR * prior + W_ACC * acc + W_TACC * tacc + W_ANCHOR * anchor
            if grounded:  # hovering bodies have no floor to keep off or feet to plant
                fz = sk.skin(A, b, floor_pts, floor_W)[..., 2]
                floor = torch.relu(-fz).pow(2).mean()
                if len(foot_X):
                    fp = sk.skin(A, b, foot_X, foot_W)
                    down = torch.sigmoid((0.02 - fp[..., 2]) / 0.006)
                    slide = (fp[1:, :, :2] - fp[:-1, :, :2]).pow(2).sum(-1)
                    skate = (down[1:] * down[:-1] * slide).mean()
                else:
                    skate = torch.zeros((), device=dev)
                loss = loss + W_FLOOR * floor + W_SKATE * skate
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
        return float(data.detach())

    t = time.time()
    run([r6, tr], 300, 0, 0.01)
    run([r6, tr], iters, 1, 0.006)
    with torch.no_grad():
        R = rot6d(r6)
        A, b = sk.transforms(R, tr)
        uv = project(P, sk.skin(A, b, X, Wq))
        px_err = ((uv - trk).norm(dim=-1) * vis).sum() / vis.sum().clamp(min=1)
    return R.cpu().numpy(), tr.detach().cpu().numpy(), dict(mean_px=round(float(px_err), 2), fit_s=round(time.time() - t, 1),
                                                            tracked=int(vis[0].sum()), joints=nj)

# ---- shaping clips --------------------------------------------------------------------------------------------------

def mat_to_quat(R):
    """(…,3,3) -> (…,4) wxyz."""
    from scipy.spatial.transform import Rotation
    q = Rotation.from_matrix(R.reshape(-1, 3, 3)).as_quat()  # xyzw
    return np.concatenate([q[:, 3:], q[:, :3]], 1).reshape(R.shape[:-2] + (4,))


def slerp_seq(q, t_src, t_dst):
    from scipy.spatial.transform import Rotation, Slerp
    T_, nj = q.shape[:2]
    out = np.empty((len(t_dst), nj, 4))
    for j in range(nj):
        xyzw = np.concatenate([q[:, j, 1:], q[:, j, :1]], 1)
        s = Slerp(t_src, Rotation.from_quat(xyzw))(np.clip(t_dst, t_src[0], t_src[-1])).as_quat()
        out[:, j] = np.concatenate([s[:, 3:], s[:, :3]], 1)
    return out


def qfix(q):
    """Same hemisphere frame to frame (and as the rest pose) so blends don't spin."""
    q = q.copy()
    if (q[0, :, 0] < 0).any():
        q[0, q[0, :, 0] < 0] *= -1
    for f in range(1, len(q)):
        flip = (q[f] * q[f - 1]).sum(-1) < 0
        q[f, flip] *= -1
    return q


def nlerp(a, b, w):
    q = a * (1 - w) + b * w
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def pose_dist(q, i, k):
    return float((1 - np.abs((q[i] * q[k]).sum(-1))).sum())


def shape_clip(q, tr, kind, fps_src=24, fps=30, seconds=None):
    q = qfix(q)
    T_ = len(q)
    t_src = np.arange(T_) / fps_src
    dur = t_src[-1]
    notes = {}
    if kind in ("loop", "move"):
        # the longest stretch (at least ~1 s) whose last pose comes back to its first: that's the cycle
        lo = max(int(0.9 * fps_src), 8)
        best = None
        for a in range(0, max(1, T_ - lo)):
            for b_ in range(a + lo, T_):
                cost = pose_dist(q, a, b_) + 0.5 * pose_dist(q, a + 1 if a + 1 < T_ else a, b_ + 1 if b_ + 1 < T_ else b_) - 0.002 * (b_ - a)
                if best is None or cost < best[0]:
                    best = (cost, a, b_)
        _, a, b_ = best
        q, tr = q[a:b_ + 1], tr[a:b_ + 1].copy()
        notes["cycle"] = [a, b_]
        # spread the remaining mismatch evenly over the cycle so the last frame lands exactly on the first
        from scipy.spatial.transform import Rotation
        n = len(q)
        xyzw = lambda a: np.concatenate([a[..., 1:], a[..., :1]], -1)  # noqa: E731
        gap = (Rotation.from_quat(xyzw(q[0])) * Rotation.from_quat(xyzw(q[-1])).inv()).as_rotvec()  # per joint
        for f in range(n):
            a_ = (Rotation.from_rotvec(gap * (f / (n - 1))) * Rotation.from_quat(xyzw(q[f]))).as_quat()
            q[f] = np.concatenate([a_[:, 3:], a_[:, :3]], 1)
        q = qfix(q)
        drift = tr[-1] - tr[0]
        tr = tr - np.outer(np.arange(n) / (n - 1), drift)
        tr[:, :2] -= tr[:, :2].mean(0)  # in place across the floor; bobbing stays
        if kind == "loop":
            tr[:, :2] *= 0.3
        t_src = np.arange(n) / fps_src
        dur = t_src[-1]
    else:
        # one-shots: from where the action starts (the clip opens on the rest pose; video models drift and redraw
        # the longer they run, so the start is the trustworthy part), the wanted length, then settle back to rest
        # (death keeps its last pose)
        energy = np.r_[0, [pose_dist(q, f, f - 1) for f in range(1, T_)]]
        want = int(round((seconds or (2.0 if kind == "death" else 1.2)) * fps_src))
        want = min(want, T_)
        csum = np.cumsum(energy)
        onset = int(np.searchsorted(csum, 0.08 * csum[-1]))
        a = max(0, min(onset - int(0.15 * fps_src), T_ - want))
        q, tr = q[a:a + want], tr[a:a + want].copy()
        notes["window"] = [a, a + want]
        tr -= tr[0]
        n = len(q)
        rest = np.zeros_like(q[0])
        rest[:, 0] = 1
        ease_in = max(2, n // 8)
        for f in range(ease_in):  # start from the rest pose the idle crossfades out of
            w = f / ease_in
            q[f] = nlerp(rest, q[f], w * w * (3 - 2 * w))
            tr[f] *= w
        if kind != "death":
            tail = max(3, n // 4)
            for i in range(tail):
                f = n - tail + i
                w = (i + 1) / tail
                q[f] = nlerp(q[f], rest, w * w * (3 - 2 * w))
                tr[f] *= 1 - w
            tr[:, :2] = np.clip(tr[:, :2], -0.25, 0.25)
        else:
            tr[:, :2] = np.clip(tr[:, :2], -0.35, 0.35)
        t_src = np.arange(n) / fps_src
        dur = t_src[-1]
    t_dst = np.linspace(0, dur, int(round(dur * fps)) + 1)  # ends exactly on the last pose (loops close)
    qo = slerp_seq(q, t_src, t_dst)
    to = np.stack([np.interp(t_dst, t_src, tr[:, k]) for k in range(3)], 1)
    return qo.astype(np.float32), to.astype(np.float32), notes


def check_sheet(d, video, qidx, tracks, tvis, R, tr, out, n=6):
    """fit/<clip>_check.png: video frames with the tracks (red) and the fitted, skinned vertices (blue) on top. Where
    blue sits on red the bones follow the video; red running off on its own is motion the rig couldn't make (or the
    video redrawing the creature)."""
    from PIL import Image, ImageDraw
    sk = Skin(d)
    T_ = len(video)
    idx = np.linspace(0, T_ - 1, n).astype(int)
    X = torch.from_numpy(d["V"][qidx]).to(dev)
    Wq = torch.from_numpy(d["W"][qidx]).to(dev)
    Wq = Wq / Wq.sum(1, keepdim=True).clamp(min=1e-6)
    with torch.no_grad():
        A, b = sk.transforms(torch.from_numpy(R[idx]).float().to(dev), torch.from_numpy(tr[idx]).float().to(dev))
        uv = project(torch.from_numpy(d["P"]).to(dev), sk.skin(A, b, X, Wq)).cpu().numpy()
    tw = 360
    th = int(tw * d["h"] / d["w"])
    sheet = Image.new("RGB", (tw * n, th))
    k = tw / d["w"]
    for c, f in enumerate(idx):
        im = Image.fromarray(video[f]).resize((tw, th))
        dr = ImageDraw.Draw(im)
        for p in range(0, len(qidx), 3):
            if tvis[f, p] > 0.5:
                x, y = tracks[f, p] * k
                dr.point((x, y), fill=(230, 40, 40))
            x, y = uv[c, p] * k
            dr.point((x, y), fill=(40, 90, 255))
        dr.text((4, 4), f"frame {f}", fill=(0, 0, 0))
        sheet.paste(im, (c * tw, 0))
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--clip", required=True)
    ap.add_argument("--kind", default="oneshot", choices=["loop", "move", "oneshot", "death"])
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--iters", type=int, default=1100)
    ap.add_argument("--hover", action="store_true", help="no floor: skip the floor and planted-feet terms")
    a = ap.parse_args()
    work = Path(a.work)
    d = load_work(work)
    t0 = time.time()
    video = read_video(a.video, d["w"], d["h"])
    qidx = pick_queries(d)
    q_pix = project(d["P"], d["V"][qidx])
    tracks, tvis = track(video, q_pix)
    R, tr, stats = fit(d, qidx, tracks, tvis, a.iters, grounded=not a.hover)
    quats = mat_to_quat(R)
    (work / "fit").mkdir(exist_ok=True)
    np.savez(work / "fit" / f"{a.clip}_raw.npz", rot=quats, trans=tr, tracks=tracks, vis=tvis, qidx=qidx)
    check_sheet(d, video, qidx, tracks, tvis, R, tr, work / "fit" / f"{a.clip}_check.png")
    qo, to, notes = shape_clip(quats, tr, a.kind, seconds=a.seconds)
    (work / "clips").mkdir(exist_ok=True)
    np.savez(work / "clips" / f"{a.clip}.npz", fps=30, rot=qo, trans=to)
    stats.update(notes, clip=a.clip, frames=len(qo), video_frames=len(video), seconds=round(time.time() - t0, 1))
    (work / "fit" / f"{a.clip}.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps({"ok": True, **stats}), flush=True)


if __name__ == "__main__":
    sys.exit(main())
