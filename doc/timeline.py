#!/usr/bin/env python3
"""Generate compatibility timeline SVG for Portable Linux GCC."""

from datetime import date
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from module.profile import ARCHES

###################
# hard-coded data #
###################

glibc_versions = [
    ("2.3.6", date(2005, 11, 4)),
    ("2.11",  date(2009, 11, 3)),
    ("2.13",  date(2011, 2, 1)),
    ("2.17",  date(2012, 12, 25)),
    ("2.19",  date(2014, 2, 7)),
    ("2.25",  date(2017, 2, 1)),
    ("2.27",  date(2018, 2, 1)),
    ("2.36",  date(2022, 8, 1)),
    ("2.43",  date(2026, 1, 24)),
]

linux_versions = [
    ("2.6.16", date(2006, 3, 20)),
    ("2.6.32", date(2009, 12, 2)),
    ("3.2",    date(2012, 1, 4)),
    ("3.7",    date(2012, 12, 10)),
    ("4.15",   date(2018, 1, 28)),
    ("5.19",   date(2022, 7, 31)),
]

###################
# calculated data #
###################

def to_decimal_year(d):
    start = date(d.year, 1, 1)
    end = date(d.year + 1, 1, 1)
    return d.year + (d - start).days / (end - start).days

glibc_year = {ver: to_decimal_year(d) for ver, d in glibc_versions}
linux_year = {ver: to_decimal_year(d) for ver, d in linux_versions}

def normalize_glibc(ver):
    if ver in glibc_year:
        return ver
    base = ".".join(ver.split(".")[:2])
    if base in glibc_year:
        return base
    raise KeyError(f"No glibc version found for '{ver}'")

_groups = {}
for key, prof in ARCHES.items():
    host = normalize_glibc(prof.glibc_host)
    gk = (host, prof.glibc_target, prof.enable_kernel)
    _groups.setdefault(gk, []).append(key)

architectures = sorted(
    [
        (" / ".join(keys), host, target, kernel)
        for (host, target, kernel), keys in _groups.items()
    ],
    key=lambda x: max(glibc_year[x[1]], linux_year[x[3]]),
)

glibc_xy = [(ver, to_decimal_year(d)) for ver, d in glibc_versions]
linux_xy = [(ver, to_decimal_year(d)) for ver, d in linux_versions]
arch_spans = [
    (name, max(glibc_year[host], linux_year[kernel]), glibc_year[target], target)
    for name, host, target, kernel in architectures
]
_latest_glibc_time = max(glibc_year.values())

all_decyears = [y for _, y in glibc_xy] + [y for _, y in linux_xy]
x_lo = int(min(all_decyears))
x_hi = int(max(all_decyears)) + 1

########
# draw #
########

# unit: pt
FONT_SIZE = 10
TL_LW = 1  # timeline line with
TL_MS = 3  # timeline marker size
TS_LW = 2  # timespan line width
TS_MS = 4  # timespan marker size

# unit: abstract (= cm)
MARGIN_L, MARGIN_R = 1.6, 0.4
MARGIN_T, MARGIN_B = 0, 0
LBL_OFF = 1 / 6
TS_LBL_OFF = 1 / 3
LATEST_DATE_DELTA = 1 / 3
TL_MARK_OFF = TL_MS * 2 / 72

# unit: abstract (= cm)
timeline_w = x_hi - x_lo
fig_w = MARGIN_L + timeline_w + MARGIN_R

# unit: abstract (= cm)
ARCH_STEP = 0.6
N = len(architectures)
arch_top = N * ARCH_STEP
arch_ys = [arch_top - ARCH_STEP * (i + 0.5) for i in range(N)]
TL_Y = arch_top + 1.3
YEAR_Y = TL_Y + 1.5
Y_HI = YEAR_Y + 0.8
fig_h = MARGIN_T + Y_HI + MARGIN_B

cmap = plt.get_cmap("Set2")
C_LINUX = cmap(0)
C_GLIBC = cmap(1)
C_ARCH = [cmap(2 + i) for i in range(N)]

plt.rcParams.update({
    "font.family": "Noto Sans",
    "font.size": FONT_SIZE,
    "font.weight": 500,
    "svg.fonttype": "none",
})

fig = plt.figure(figsize=(fig_w / 2.54, fig_h / 2.54), facecolor="white")
lf = MARGIN_L / fig_w
bf = MARGIN_B / fig_h
wf = timeline_w / fig_w
hf = Y_HI / fig_h
ax = fig.add_axes((lf, bf, wf, hf))
ax.set_xlim(x_lo, x_hi)
ax.set_ylim(0, Y_HI)
ax.axis("off")

# year ticks
for yr in range(x_lo, x_hi + 1):
    ax.plot([yr, yr], [YEAR_Y, YEAR_Y + LBL_OFF], color="#cccccc", lw=TL_LW)
    if yr % 2 == 0:
        ax.text(yr, YEAR_Y + LBL_OFF * 2, str(yr), ha="center", va="bottom", color="#999999")

# timeline
ax.plot([x_lo, x_hi], [TL_Y, TL_Y], color="#999999", lw=TL_LW)
ax.text(x_lo - LBL_OFF, TL_Y + LBL_OFF, "Linux", ha="right", va="bottom", color=C_LINUX)
for ver, x in linux_xy:
    ax.plot(x, TL_Y + TL_MARK_OFF, "v", color=C_LINUX, ms=TL_MS)
    ax.text(x, TL_Y + TL_MARK_OFF + LBL_OFF, ver, ha="left", va="bottom", color=C_LINUX, rotation=45)
ax.text(x_lo - LBL_OFF, TL_Y - LBL_OFF, "Glibc", ha="right", va="top", color=C_GLIBC)
for ver, x in glibc_xy:
    ax.plot(x, TL_Y - TL_MARK_OFF, "^", color=C_GLIBC, ms=TL_MS)
    ax.text(x, TL_Y - TL_MARK_OFF - LBL_OFF, ver, ha="right", va="top", color=C_GLIBC, rotation=45)

# architecture spans
for i, ((name, x1, x2, target_ver), color) in enumerate(zip(arch_spans, C_ARCH)):
    y = arch_ys[i]
    ax.plot(x1, y, 'o', color=color, ms=TS_MS)
    if glibc_year[target_ver] == _latest_glibc_time:
        x2 = x2 + LATEST_DATE_DELTA
        ax.plot([x1, x2], [y, y], color=color, lw=TS_LW)
        ax.plot(x2, y, '>', color=color, ms=TS_MS)
        ax.text(x1 - TS_LBL_OFF, y, name, ha="right", va="center", color="#666666", clip_on=False)
    else:
        ax.plot([x1, x2], [y, y], color=color, lw=TS_LW)
        ax.plot(x2, y, 'o', color=color, ms=TS_MS)
        ax.text(x2 + TS_LBL_OFF, y, name, ha="left", va="center", color="#cccccc", clip_on=False)

# save
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timeline.svg")
fig.savefig(out, format="svg", facecolor="white")
plt.close()
print(f"Generated {out}")
