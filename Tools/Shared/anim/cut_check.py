"""Cut scores of a work folder's clips (see wan_video.cut_score): python cut_check.py <work> -> {"clip": score, ...}"""
import json, sys
from pathlib import Path

import imageio.v3 as iio
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wan_video import cut_score  # noqa: E402

work = Path(sys.argv[1])
print(json.dumps({p.stem: round(cut_score(iio.imread(p).astype(np.float32) / 255.0), 4) for p in sorted((work / "video").glob("*.mp4"))}))
