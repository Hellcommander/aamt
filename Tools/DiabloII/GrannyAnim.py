"""Read, pose, edit and write the animation clips of a Diablo II: Resurrected HD monster.

A monster's clips live in one Granny file, `<monster>/animation/combined.animations`:
one Animation per clip (attack1, walk, neutral, ...), each with a transform track
per bone. The state machine JSON names clips as `<folder>/animation/<clip>.animation`.

    anim = GrannyAnim.load(path_or_bytes)            # Granny.py tree underneath
    anim.names()                                     # ['attack1', 'attack2', ...]
    clip = anim.clip('walk')                         # Clip: duration, tracks
    pose = clip.pose(0.25)                           # {bone: Local(position, quaternion xyzw, 3x3 scale)}
    world = GrannyAnim.world(skeleton, pose)         # {bone: (3x3 rows, position)} in model space

    new = clip.resample(fps=30)                      # Keys: times + a pose per time, free to edit
    new.rotate_world(skeleton, 'spine_02_bind_jnt', axis=(1, 0, 0), degrees=lambda t: 20 * t)
    anim.add('cast', new)                            # written as plain linear keys
    anim.save(out_path)

Reading stock clips: the game stores B-spline curves with quantised knots and
controls. They are decoded exactly, but then treated as keyframes (control i at
knot i, straight lines between), the way other Granny tools do. Stock curves
have a control every 1/30 s, so the difference from the true spline is a slight
smoothing, not a different motion. Clips written here use degree-1 curves with
32-bit float keys (DaK32fC32f), which are exactly what was authored.

Conventions (checked against the skeleton's own inverse world matrices):
row vectors, world = local x parent world, quaternions are x, y, z, w.
"""
import copy
import math
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import Granny  # noqa: E402

IDENTITY_Q = np.array([0.0, 0.0, 0.0, 1.0])
IDENTITY_S = np.eye(3)

# Granny's table for quantised quaternions (curve formats D4nK16uC15u and D4nK8uC7u).
_SQRT = 1.4142135623730951
_SCALES = [_SQRT, _SQRT / 2, _SQRT / 4, _SQRT / 4, _SQRT / 4, _SQRT / 8, _SQRT / 8, _SQRT / 8]
_SCALES = _SCALES + [-v for v in _SCALES]
_OFFSETS = [-_SQRT / 2, -_SQRT / 4, -0.53033006, -_SQRT / 8, _SQRT / 8, -_SQRT / 8, -_SQRT / 16, 0.0]
_OFFSETS = _OFFSETS + [-v for v in _OFFSETS]


def _float_from_trunc(value):
    return struct.unpack('<f', struct.pack('<I', (value & 0xFFFF) << 16))[0]


def _quats(entries, raw, bits):
    """Controls of a D4n curve: three integers per key -> unit quaternions (x, y, z, w)."""
    top = 1 << bits
    mask = top - 1
    scale = [_SCALES[(entries >> (4 * i)) & 15] / mask for i in range(4)]
    offset = [_OFFSETS[(entries >> (4 * i)) & 15] for i in range(4)]
    raw = np.asarray(raw, dtype=np.int64).reshape(-1, 3)
    a, b, c = raw[:, 0], raw[:, 1], raw[:, 2]
    s1 = (((b & top) >> bits) << 1) | ((c & top) >> bits)       # the component that is not stored
    out = np.zeros((len(raw), 4))
    rows = np.arange(len(raw))
    total = np.zeros(len(raw))
    for step, data in ((1, a), (2, b), (3, c)):
        which = (s1 + step) & 3
        value = (data & mask) * np.array(scale)[which] + np.array(offset)[which]
        out[rows, which] = value
        total += value * value
    last = np.sqrt(np.clip(1.0 - total, 0.0, None))
    out[rows, s1] = np.where(a & top, -last, last)
    return out


def decode_curve(curve):
    """A curve as keyframes: (times or None, values N x dim). None, None = identity."""
    data = curve['CurveData']
    value = data['$value']
    header = next(k for k in value if k.startswith('CurveDataHeader_'))
    kind = header[len('CurveDataHeader_'):]
    if kind == 'DaIdentity':
        return None, None
    if kind in ('D3Constant32f', 'D4Constant32f', 'DaConstant32f'):
        return None, np.array(value['Controls'], dtype=np.float64)[None, :]
    if kind == 'DaK32fC32f':
        knots = np.array(value['Knots'], dtype=np.float64)
        return knots, np.array(value['Controls'], dtype=np.float64).reshape(len(knots), -1)
    if kind == 'DaKeyframes32f':
        controls = np.array(value['Controls'], dtype=np.float64).reshape(-1, value['Dimension'])
        return 'uniform', controls
    kc = value['KnotsControls']
    if kind in ('D4nK16uC15u', 'D4nK8uC7u'):
        n = len(kc) // 4
        knots = np.array(kc[:n], dtype=np.float64) / value['OneOverKnotScale']
        return knots, _quats(value['ScaleOffsetTableEntries'], kc[n:], 15 if kind == 'D4nK16uC15u' else 7)
    if kind in ('D3K16uC16u', 'D3K8uC8u', 'D3I1K16uC16u', 'D3I1K8uC8u'):
        one = 'I1' in kind
        n = len(kc) // (2 if one else 4)
        knots = np.array(kc[:n], dtype=np.float64) / _float_from_trunc(value['OneOverKnotScaleTrunc'])
        controls = np.array(kc[n:], dtype=np.float64).reshape(n, 1 if one else 3)
        return knots, np.array(value['ControlOffsets']) + controls * np.array(value['ControlScales'])
    if kind in ('D9I1K16uC16u', 'D9I1K8uC8u'):
        # A uniform scale: one stored number s per key, the 3x3 scale-shear is s times identity
        # (players' weapon attach bones: the weapon shrinks away when it is thrown).
        n = len(kc) // 2
        knots = np.array(kc[:n], dtype=np.float64) / _float_from_trunc(value['OneOverKnotScaleTrunc'])
        s = value['ControlOffset'] + np.array(kc[n:], dtype=np.float64) * value['ControlScale']
        return knots, s[:, None] * np.eye(3).reshape(1, 9)
    if kind in ('D9I3K16uC16u', 'D9I3K8uC8u'):
        # A scale per axis: three stored numbers per key on the diagonal of the scale-shear.
        n = len(kc) // 4
        knots = np.array(kc[:n], dtype=np.float64) / _float_from_trunc(value['OneOverKnotScaleTrunc'])
        d = np.array(value['ControlOffsets']) + np.array(kc[n:], dtype=np.float64).reshape(n, 3) * np.array(value['ControlScales'])
        out = np.zeros((n, 9))
        out[:, 0], out[:, 4], out[:, 8] = d[:, 0], d[:, 1], d[:, 2]
        return knots, out
    raise NotImplementedError(f'curve format {kind} is not decoded yet')


def _at(times, values, t, quaternion=False):
    if values is None:
        return None
    if times is None or len(values) == 1:
        return values[0]
    i = int(np.searchsorted(times, t, side='right'))
    if i <= 0:
        return values[0]
    if i >= len(times):
        return values[-1]
    t0, t1 = times[i - 1], times[i]
    f = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
    a, b = values[i - 1], values[i]
    if quaternion and float(a @ b) < 0:
        b = -b
    out = a + (b - a) * f
    return out / np.linalg.norm(out) if quaternion else out


class Local:
    """A bone's transform relative to its parent."""
    __slots__ = ('position', 'rotation', 'scale')

    def __init__(self, position=None, rotation=None, scale=None):
        self.position = np.zeros(3) if position is None else np.asarray(position, dtype=np.float64)
        self.rotation = IDENTITY_Q.copy() if rotation is None else np.asarray(rotation, dtype=np.float64)
        self.scale = IDENTITY_S.copy() if scale is None else np.asarray(scale, dtype=np.float64).reshape(3, 3)

    def copy(self):
        return Local(self.position.copy(), self.rotation.copy(), self.scale.copy())


def quat_matrix(q):
    """Rotation matrix for row vectors (v' = v @ M)."""
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)],
        [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)],
        [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)],
    ])


def matrix_quat(m):
    """Inverse of quat_matrix."""
    m = np.asarray(m).T                    # to the column-vector form the textbook formula uses
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]
    q = np.array(q)
    return q / np.linalg.norm(q)


def axis_rotation(axis, degrees):
    """Rotation matrix (row vectors) about an axis, right-handed."""
    axis = np.asarray(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    half = math.radians(degrees) / 2
    return quat_matrix(np.append(axis * math.sin(half), math.cos(half)))


class Skeleton:
    """Bone names, parents, rest pose and bind matrices from a .skeleton or .model file."""

    def __init__(self, source):
        tree = source if isinstance(source, dict) else Granny.read(_bytes(source)).root()
        bones = tree['Skeletons'][0]['Bones']
        self.names = [b['Name'] for b in bones]
        self.parents = [b['ParentIndex'] for b in bones]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.rest = {}
        self.inverse_bind = {}
        for b in bones:
            t = b.get('LocalTransform') or b['Transform']
            self.rest[b['Name']] = Local(t['position'], t['orientation'], t['scale_shear'])
            self.inverse_bind[b['Name']] = np.array(b['InverseWorldTransform'], dtype=np.float64).reshape(4, 4)

    def children(self, name):
        i = self.index[name]
        return [n for n, p in zip(self.names, self.parents) if p == i]


def _bytes(source):
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    with open(source, 'rb') as f:
        return f.read()


def world(skeleton, pose):
    """{bone: 4x4 (row vectors)} in model space for a pose; bones missing from the pose use their rest transform."""
    out = {}
    for name, parent in zip(skeleton.names, skeleton.parents):
        local = pose.get(name) or skeleton.rest[name]
        m = np.eye(4)
        m[:3, :3] = local.scale @ quat_matrix(local.rotation)
        m[3, :3] = local.position
        out[name] = m if parent < 0 else m @ out[skeleton.names[parent]]
    return out


def skin(mesh_positions, weights, indices, bone_names, skeleton, pose):
    """Mesh vertices (bind pose) moved by a pose. weights/indices as GrannyMesh.Mesh.weights() gives them."""
    w = world(skeleton, pose)
    homo = np.concatenate([mesh_positions, np.ones((len(mesh_positions), 1))], axis=1)
    out = np.zeros((len(mesh_positions), 3))
    for slot in range(weights.shape[1]):
        for k in np.unique(indices[:, slot]):
            rows = (indices[:, slot] == k) & (weights[:, slot] > 0)
            if not rows.any():
                continue
            name = bone_names[k]
            m = skeleton.inverse_bind[name] @ w[name]
            out[rows] += (homo[rows] @ m)[:, :3] * weights[rows, slot][:, None]
    return out


class Clip:
    """One stock clip, read-only: sampled through pose()."""

    def __init__(self, animation, group=None):
        """group: the track group to read, by name. Monster clips have one; player clips have one per
        armour part plus "root" (the skeleton), and the skeleton's is the one wanted then."""
        self.source = animation
        self.name = animation['Name']
        self.duration = animation['Duration']
        self.time_step = animation['TimeStep']
        groups = animation['TrackGroups']
        self.group = group if group is not None else ('root' if any(g['Name'] == 'root' for g in groups) and len(groups) > 1 else None)
        group = next(g for g in groups if g['Name'] == self.group) if self.group is not None else groups[0]
        self.tracks = {}
        for track in group['TransformTracks']:
            self.tracks[track['Name']] = tuple(decode_curve(track[key]) for key in ('PositionCurve', 'OrientationCurve', 'ScaleShearCurve'))

    def _times(self, times, count):
        if isinstance(times, str):          # 'uniform': keyframes spread over the clip
            return np.linspace(0.0, self.duration, count)
        return times

    def pose(self, t):
        out = {}
        for name, ((pt, pv), (rt, rv), (st, sv)) in self.tracks.items():
            position = _at(self._times(pt, 0 if pv is None else len(pv)), pv, t)
            rotation = _at(self._times(rt, 0 if rv is None else len(rv)), rv, t, quaternion=True)
            scale = _at(self._times(st, 0 if sv is None else len(sv)), sv, t)
            out[name] = Local(position, None if rotation is None else rotation / np.linalg.norm(rotation), scale)
        return out

    def resample(self, fps=30.0, duration=None, start=0.0, end=None):
        """Editable keys taken from this clip. duration stretches or squeezes the result in time."""
        end = self.duration if end is None else end
        count = max(2, int(round((end - start) * fps)) + 1)
        source_times = np.linspace(start, end, count)
        out_duration = (end - start) if duration is None else duration
        keys = Keys(np.linspace(0.0, out_duration, count), [self.pose(t) for t in source_times], self.source)
        keys.group = self.group
        return keys


class Keys:
    """An editable clip: a pose for each time. Edits act on every key."""

    def __init__(self, times, poses, template, group=None):
        self.times = np.asarray(times, dtype=np.float64)
        self.poses = poses
        self.template = template            # the stock Animation whose flags, vector tracks and second group are reused
        self.group = group                  # the track group the keys belong to (None: the first)

    @property
    def duration(self):
        return float(self.times[-1])

    def _amount(self, value, k):
        return value(self.times[k] / self.duration if self.duration else 0.0) if callable(value) else value

    def rotate_world(self, skeleton, bone, axis, degrees):
        """Turns a bone (and so everything below it) about a model-space axis through its joint.

        degrees: a number, or a function of the clip's progress 0..1.
        """
        for k, pose in enumerate(self.poses):
            amount = self._amount(degrees, k)
            if not amount:
                continue
            w = world(skeleton, pose)
            parent = skeleton.parents[skeleton.index[bone]]
            parent_rot = np.eye(3) if parent < 0 else _rotation_part(w[skeleton.names[parent]][:3, :3])
            mine = _rotation_part(w[bone][:3, :3])
            new_world = mine @ axis_rotation(axis, amount)
            local = pose[bone] = (pose.get(bone) or skeleton.rest[bone]).copy()
            local.rotation = matrix_quat(new_world @ parent_rot.T)

    def scale(self, bones, factor):
        """Scales bones in place (a quill joint: the quill grows from its root)."""
        for k, pose in enumerate(self.poses):
            amount = self._amount(factor, k)
            for bone in bones:
                local = pose[bone] = pose[bone].copy()
                local.scale = local.scale * amount

    def move(self, skeleton, bone, offset):
        """Shifts a bone by a model-space offset (x, y, z), a triple or a function of progress."""
        for k, pose in enumerate(self.poses):
            amount = np.asarray(self._amount(offset, k), dtype=np.float64)
            if not amount.any():
                continue
            w = world(skeleton, pose)
            parent = skeleton.parents[skeleton.index[bone]]
            basis = np.eye(3) if parent < 0 else w[skeleton.names[parent]][:3, :3]
            local = pose[bone] = pose[bone].copy()
            local.position = local.position + amount @ np.linalg.inv(basis)

    def blend_to(self, other_pose, weight):
        """Mixes every key towards a fixed pose; weight is a number or a function of progress."""
        for k, pose in enumerate(self.poses):
            w = self._amount(weight, k)
            if not w:
                continue
            for bone, target in other_pose.items():
                local = pose[bone] = pose[bone].copy()
                local.position = local.position + (target.position - local.position) * w
                b = target.rotation if float(local.rotation @ target.rotation) >= 0 else -target.rotation
                q = local.rotation + (b - local.rotation) * w
                local.rotation = q / np.linalg.norm(q)
                local.scale = local.scale + (target.scale - local.scale) * w

    def append(self, other):
        """Plays another set of keys after this one."""
        self.times = np.concatenate([self.times, self.duration + other.times[1:]])
        self.poses = self.poses + other.poses[1:]

    def reversed(self):
        return Keys(self.times.copy(), self.poses[::-1], self.template, self.group)

    def mirrored(self, skeleton, axis=0, partner=None):
        """The same motion done by the other side of the body: a right-hand throw becomes a left-hand one.

        Every key is posed in model space, reflected across the plane normal to `axis` (0 = X, the
        side-to-side axis of D2R characters), and each bone takes the reflected pose of its partner
        (left <-> right by name, see mirror_name). Bones' own axes are not assumed to be mirrored:
        a per-bone correction taken from the rest pose keeps the mirrored rest pose equal to the rest
        pose, so any rig works. Bones without a partner (spine, head) are reflected in place.
        """
        partner = partner or mirror_name
        reflect = np.eye(4)
        reflect[axis, axis] = -1.0
        rest = world(skeleton, {})
        pairs = {n: (partner(n) if partner(n) in skeleton.index else n) for n in skeleton.names}
        fix = {n: rest[n] @ np.linalg.inv(reflect @ rest[pairs[n]] @ reflect) for n in skeleton.names}
        # A bone off the middle without a partner (the Assassin's shield_attach on the left forearm)
        # cannot be reflected in place: it keeps its own local pose and follows its mirrored parent.
        side_only = {n for n in skeleton.names if pairs[n] == n and abs(rest[n][3, axis]) > 1e-3 * max(1.0, float(np.abs(rest[n][3, :3]).max()))}
        out = []
        for pose in self.poses:
            w = world(skeleton, pose)
            new_world = {}
            for n, p in zip(skeleton.names, skeleton.parents):
                if n in side_only:
                    local = pose.get(n) or skeleton.rest[n]
                    m = np.eye(4)
                    m[:3, :3] = local.scale @ quat_matrix(local.rotation)
                    m[3, :3] = local.position
                    new_world[n] = m if p < 0 else m @ new_world[skeleton.names[p]]
                else:
                    new_world[n] = fix[n] @ reflect @ w[pairs[n]] @ reflect
            new_pose = {}
            for name in pose:
                if name not in skeleton.index:
                    new_pose[name] = pose[name].copy()
                    continue
                if name in side_only:
                    new_pose[name] = pose[name].copy()
                    continue
                parent = skeleton.parents[skeleton.index[name]]
                local = new_world[name] if parent < 0 else new_world[name] @ np.linalg.inv(new_world[skeleton.names[parent]])
                source = pose.get(pairs[name]) or skeleton.rest[pairs[name]]
                new_pose[name] = Local(local[3, :3].copy(), matrix_quat(_rotation_part(local[:3, :3])), source.scale.copy())
            out.append(new_pose)
        return Keys(self.times.copy(), out, self.template, self.group)

    def bounds(self, skeleton):
        """Model-space box of the joints over the clip, padded: what the clip's bbAnim wants."""
        low, high = np.full(3, np.inf), np.full(3, -np.inf)
        for pose in self.poses[::max(1, len(self.poses) // 12)]:
            points = np.array([m[3, :3] for m in world(skeleton, pose).values()])
            low, high = np.minimum(low, points.min(0)), np.maximum(high, points.max(0))
        pad = (high - low).max() * 0.2
        return (low - pad).tolist(), (high + pad).tolist()


def _rotation_part(m):
    """Rotation of a 3x3 that may carry scale."""
    u, _, vt = np.linalg.svd(m)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] = -u[:, -1]
        r = u @ vt
    return r


# --- writing ---

def _header(kind, fmt, degree):
    name = f'CurveDataHeader_{kind}'
    return name, {'name': name, 'type': 'inline', 'of': [{'name': 'Format', 'type': 'uint8'}, {'name': 'Degree', 'type': 'uint8'}]}, {'Format': fmt, 'Degree': degree}


def _identity(dimension):
    name, member, value = _header('DaIdentity', 2, 0)
    return {'CurveData': {'$type': [member, {'name': 'Dimension', 'type': 'int16'}], '$value': {name: value, 'Dimension': dimension}}}


def _constant(values):
    kind = {3: 'D3Constant32f', 4: 'D4Constant32f'}[len(values)]
    name, member, value = _header(kind, {3: 4, 4: 5}[len(values)], 0)
    return {'CurveData': {'$type': [member, {'name': 'Padding', 'type': 'int16'}, {'name': 'Controls', 'type': 'real32', 'width': len(values)}],
                          '$value': {name: value, 'Padding': 0, 'Controls': [float(v) for v in values]}}}


def _linear(times, values):
    name, member, value = _header('DaK32fC32f', 1, 1)
    return {'CurveData': {'$type': [member, {'name': 'Padding', 'type': 'int16'},
                                    {'name': 'Knots', 'type': 'ref_array', 'of': [{'name': 'Real32', 'type': 'real32'}]},
                                    {'name': 'Controls', 'type': 'ref_array', 'of': [{'name': 'Real32', 'type': 'real32'}]}],
                          '$value': {name: value, 'Padding': 0, 'Knots': [float(t) for t in times],
                                     'Controls': [float(v) for v in np.asarray(values).reshape(-1)]}}}


def _curve(times, values, identity, tolerance):
    values = np.asarray(values, dtype=np.float64)
    if np.abs(values - values[0]).max() <= tolerance:
        if np.abs(values[0] - identity).max() <= tolerance:
            return _identity(len(identity))
        if len(identity) in (3, 4):
            return _constant(values[0])
    return _linear(times, values)


class Animations:
    def __init__(self, source):
        self.file = Granny.read(_bytes(source))
        self.tree = self.file.root()
        self.type = self.file.describe(self.file.root_type) if hasattr(self.file, 'root_type') else None

    def names(self):
        return [a['Name'] for a in self.tree['Animations']]

    def clip(self, name):
        for a in self.tree['Animations']:
            if a['Name'] == name:
                return Clip(a)
        raise KeyError(f'no clip "{name}"; this file has {self.names()}')

    def add(self, name, keys, skeleton=None):
        """Adds (or replaces) a clip made of editable keys."""
        animation = copy.deepcopy(keys.template)
        animation['Name'] = name
        animation['Duration'] = keys.duration
        wanted = getattr(keys, 'group', None)
        group = next(g for g in animation['TrackGroups'] if g['Name'] == wanted) if wanted is not None else animation['TrackGroups'][0]
        order = [t['Name'] for t in group['TransformTracks']]
        tracks = []
        for bone in order:
            locals_ = [pose[bone] for pose in keys.poses]
            rotations = np.array([l.rotation for l in locals_])
            for k in range(1, len(rotations)):           # keep neighbours on the same side so straight lines are short
                if float(rotations[k] @ rotations[k - 1]) < 0:
                    rotations[k] = -rotations[k]
            tracks.append({
                'Name': bone, 'Flags': 0,
                'OrientationCurve': _curve(keys.times, rotations, IDENTITY_Q, 1e-6),
                'PositionCurve': _curve(keys.times, [l.position for l in locals_], np.zeros(3), 1e-7),
                'ScaleShearCurve': _curve(keys.times, [l.scale.reshape(9) for l in locals_], IDENTITY_S.reshape(9), 1e-6),
            })
        group['TransformTracks'] = tracks
        if skeleton is not None and isinstance(animation.get('ExtendedData'), dict):
            low, high = keys.bounds(skeleton)
            target = animation['ExtendedData'].get('$value', animation['ExtendedData'])
            if 'bbAnimMin' in target:
                target['bbAnimMin'], target['bbAnimMax'] = low, high
        self.tree['Animations'] = [a for a in self.tree['Animations'] if a['Name'] != name] + [animation]
        self.tree['Animations'].sort(key=lambda a: a['Name'])

    def to_bytes(self):
        writer = Granny.Writer(self.file.tag, tuple(self.file.extra_tags)) if hasattr(self.file, 'tag') else Granny.Writer()
        return writer.build(self.type, self.tree)

    def save(self, path):
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(self.to_bytes())


def load(source):
    return Animations(source)


# --- clips from a description (what a preset holds) ---

def _curve_function(points, wave=None, ease=True):
    """[[progress, value], ...] -> smooth function of progress 0..1. value: a number or a list of numbers.

    wave: {"cycles": n, "amplitude": a} adds a sine of that size, faded in and out with the clip;
    with "fade": false it runs at full size throughout (whole cycles then loop seamlessly), and
    "phase" (degrees) shifts it.
    ease False: straight lines between the points (an even turn, e.g. 0 -> 360 for a looping spin)
    instead of easing in and out of each point.
    """
    points = sorted(([float(p), np.asarray(v, dtype=np.float64)] for p, v in points), key=lambda item: item[0])

    def value(progress):
        if progress <= points[0][0]:
            out = points[0][1]
        elif progress >= points[-1][0]:
            out = points[-1][1]
        else:
            for (p0, v0), (p1, v1) in zip(points, points[1:]):
                if p0 <= progress <= p1:
                    f = 0.0 if p1 <= p0 else (progress - p0) / (p1 - p0)
                    if ease:
                        f = f * f * (3 - 2 * f)             # ease in and out
                    out = v0 + (v1 - v0) * f
                    break
        if wave:
            envelope = math.sin(math.pi * progress) if wave.get('fade', True) else 1.0
            phase = math.radians(wave.get('phase', 0.0))
            amplitude = np.asarray(wave['amplitude'], dtype=np.float64)      # a number, or x, y, z for a move
            out = out + amplitude * (math.sin(2 * math.pi * wave['cycles'] * progress + phase) * envelope)
        return out if np.ndim(out) else float(out)
    return value


def _bones_named(skeleton, spec):
    """A bone name, a list of names, or {"prefix", "first", "last"} (numbered joints such as spike_NN_jnt)."""
    if isinstance(spec, str):
        return [spec]
    if isinstance(spec, list):
        return spec
    out = []
    for name in skeleton.names:
        if not name.startswith(spec['prefix']):
            continue
        digits = ''.join(ch for ch in name[len(spec['prefix']):] if ch.isdigit())
        number = int(digits) if digits else 0
        if spec.get('first', 0) <= number <= spec.get('last', 10 ** 9):
            out.append(name)
    return out


def build_clip(animations, skeleton, spec):
    """Makes a clip from a description and adds it to `animations`.

    spec: {"name": "cast", "base": "neutral", "duration": 0.8, "fps": 30, "from": 0.0, "to": 0.8,
           "edits": [
             {"rotate": "spine_01_bind_jnt", "axis": [1, 0, 0], "degrees": [[0, 0], [0.4, -30], [1, 0]]},
             {"scale": {"prefix": "spike_", "first": 20, "last": 62}, "factor": [[0, 1], [0.5, 1.3], [1, 1]]},
             {"move": "pelvis_bind_jnt", "offset": [[0, [0, 0, 0]], [0.5, [0, -0.2, 0]], [1, [0, 0, 0]]]}
           ]}
    base is a clip of the same file; from/to cut a piece of it (seconds) and duration retimes the piece.
    "at": <seconds> instead holds the base's pose at that time for `duration` (keys at `fps`).
    Instead of base, "parts": [{base, from, to, duration, edits}, ...] plays several pieces in a row.
    Curves are [progress 0..1, value] pairs, eased between ("ease": "linear" on an edit: straight lines);
    an edit may add "wave": {"cycles", "amplitude", "fade": true, "phase": 0}.
    Axes and offsets are in model space (D2R monsters: +Y up, +Z towards the head).
    """
    if 'parts' in spec:
        # Several pieces played one after another, each made like a clip of its own; edits on the
        # clip itself then run over the whole result.
        keys = None
        for part in spec['parts']:
            piece = _keys_for(animations, skeleton, part)
            if keys is None:
                keys = piece
            else:
                keys.append(piece)
    else:
        keys = _keys_for(animations, skeleton, {k: v for k, v in spec.items() if k != 'edits'})
    _apply_edits(keys, skeleton, spec.get('edits', []), spec['name'])
    animations.add(spec['name'], keys, skeleton)
    return keys


def _keys_for(animations, skeleton, spec):
    base = animations.clip(spec['base'])
    if 'at' in spec:
        # One pose of the base clip held for the whole duration: the edits then carry all of the
        # motion (a wing gesture from a still glide pose, without the base's own flapping).
        fps = spec.get('fps', 30.0)
        if 'duration' not in spec:
            raise ValueError(f"clip {spec.get('name', spec['base'])}: \"at\" needs a \"duration\"")
        held = base.pose(float(spec['at']))
        count = max(2, int(round(spec['duration'] * fps)) + 1)
        keys = Keys(np.linspace(0.0, spec['duration'], count), [{b: l.copy() for b, l in held.items()} for _ in range(count)], base.source)
        keys.group = base.group
    else:
        keys = base.resample(fps=spec.get('fps', 30.0), duration=spec.get('duration'),
                             start=spec.get('from', 0.0), end=spec.get('to'))
    _apply_edits(keys, skeleton, spec.get('edits', []), spec.get('name', spec['base']))
    return keys


def _apply_edits(keys, skeleton, edits, label):
    for edit in edits:
        ease = edit.get('ease', 'smooth') != 'linear'
        if 'rotate' in edit:
            for bone in _bones_named(skeleton, edit['rotate']):     # each about its own joint
                keys.rotate_world(skeleton, bone, edit.get('axis', [1, 0, 0]), _curve_function(edit['degrees'], edit.get('wave'), ease))
        elif 'scale' in edit:
            keys.scale(_bones_named(skeleton, edit['scale']), _curve_function(edit['factor'], edit.get('wave'), ease))
        elif 'move' in edit:
            keys.move(skeleton, edit['move'], _curve_function(edit['offset'], edit.get('wave'), ease))
        else:
            raise ValueError(f"clip {label}: an edit needs \"rotate\", \"scale\" or \"move\"")


def mirror_name(name):
    """Name of the bone on the other side: *_L_* <-> *_R_*, L_* <-> R_*, *_L <-> *_R (either case). Others: unchanged."""
    for left, right in (('_L_', '_R_'), ('_l_', '_r_')):
        if left in name:
            return name.replace(left, right)
        if right in name:
            return name.replace(right, left)
    for left, right in (('L_', 'R_'), ('l_', 'r_')):
        if name.startswith(left):
            return right + name[len(left):]
        if name.startswith(right):
            return left + name[len(right):]
    for left, right in (('_L', '_R'), ('_l', '_r')):
        if name.endswith(left):
            return name[:-len(left)] + right
        if name.endswith(right):
            return name[:-len(right)] + left
    return name
