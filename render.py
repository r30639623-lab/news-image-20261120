#!/usr/bin/env python3
"""Render news.png v13 — a dense one-page digest summing up world news
for Friday, 20 November 2026: 36 stories in one 1024x1024 image.

Run:  python3 render.py
Writes: news.png (1024 x 1024, PNG, <= 1 MiB)

Design v13 (built on v12 — same 36 verified stories, same premium
navy + gold + warm-white palette, same masthead, same 3-column
layout). The user asked for one more level up ("biar mantep kalau
juri liatnya" — so the judge is impressed at first sight), so v13
attacks the two things a judge notices first: photos and the hero.

- FOUR DARKEST THUMBNAILS REPLACED with bright, sharp
  photo-realistic illustrations (measured, not guessed: the old
  thumbs were mean brightness 20 / 44 / 60 / 89; the new ones are
  99 / 120 / 148 / 122): Markets (near-black red chart -> bright
  trading floor with a big falling chart), Riyadh (night shot ->
  sunny daytime Kingdom Centre), Nepal (a 1973 hashish shop, odd
  and dark -> sunny Kathmandu with the Himalayas), IEA data
  centers (dark server photo -> bright white data-center
  corridor). All four are labelled as AI-generated illustrations
  in assets/thumbs.json.
- EVERY REMAINING THUMBNAIL gets a deterministic lift at load
  time (brightness + autocontrast for dark ones, mild sharpening
  for all), so no photo on the page reads as a dark smudge any
  more — e.g. the dusk Miami and Sydney shots.
- HERO made more dramatic: the Peace Palace crop is re-centred
  on the building (cy 0.62 instead of 0.5), colour/contrast
  richer, scrim and bottom gradient stronger, so the white
  headline sits on the photo instead of floating over sky.
- MASTHEAD finished properly: a thin gold rule under the
  ink+red rules, and a small gold square opening the section
  header — the two details a print designer would add.
- One headline reworded for a clean break (facts identical):
  "IMF: global debt nears 100% of GDP" wrapped with a lone
  "GDP" on line two; it is now "IMF: global debt nears 100%
  of world GDP", which breaks "…of / world GDP".

Facts: the same 36 verified stories as v8–v12 — nothing added,
removed or changed.

Only Pillow + fonts shipped with this VM are used. No network:
all photos are embedded in assets/ and assets/thumbs/.
"""
import os

from PIL import (Image, ImageDraw, ImageFont, ImageOps, ImageEnhance,
                 ImageStat, ImageFilter)

W, H = 1024, 1024
OUT = "news.png"
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
THUMBS = os.path.join(ASSETS, "thumbs")
MAX_BYTES = 1024 * 1024  # 1 MiB

PAPER = (253, 252, 248)      # warm white paper
INK = (24, 33, 44)           # deep blue-ink
INK_SOFT = (48, 60, 74)
SLATE = (99, 110, 124)
HAIR = (203, 196, 180)       # hairline rules
GOLD = (166, 134, 71)        # muted gold
GOLD_LT = (226, 186, 108)    # gold readable on a dark photo
RED = (154, 43, 38)          # muted Economist-style red
WHITE = (255, 255, 255)
WHITE_SOFT = (232, 236, 240)
CHIP = (10, 16, 24)

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SERIF_IT = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_w):
    """Greedy word wrap measured with the real font."""
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_lines(draw, lines, x, y, fnt, fill, lh):
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def tracked_width(draw, text, fnt, tr):
    w = 0
    for ch in text:
        w += draw.textlength(ch, font=fnt)
    return w + tr * max(0, len(text) - 1)


def draw_tracked(draw, x, y, text, fnt, fill, tr):
    """Draw text with letter-spacing `tr`; returns x after last char."""
    cx = x
    for ch in text:
        draw.text((cx, y), ch, font=fnt, fill=fill)
        cx += draw.textlength(ch, font=fnt) + tr
    return cx


def wrap_mixed(draw, parts, max_w):
    """Greedy wrap of a multi-font paragraph.

    `parts` is a list of (text, font, fill); words keep the font and
    colour of their part. Returns lines: lists of (word, font, fill).
    """
    words = []
    for text, fnt, fill in parts:
        for w in text.split():
            words.append((w, fnt, fill))
    lines, cur, cur_w = [], [], 0
    for w, fnt, fill in words:
        ww = draw.textlength(w + " ", font=fnt)
        if cur and cur_w + ww > max_w:
            lines.append(cur)
            cur, cur_w = [], 0
        cur.append((w, fnt, fill))
        cur_w += ww
    if cur:
        lines.append(cur)
    return lines


def draw_mixed(draw, lines, x, y, lh):
    """Draw wrap_mixed lines; returns y after the last line."""
    for line in lines:
        cx = x
        for w, fnt, fill in line:
            draw.text((cx, y), w, font=fnt, fill=fill)
            cx += draw.textlength(w + " ", font=fnt)
        y += lh
    return y


def cover(path, w, h, cx=0.5, cy=0.5):
    """Centre-crop `path` to exactly w x h (deterministic)."""
    im = Image.open(os.path.join(ASSETS, path)).convert("RGB")
    return ImageOps.fit(im, (w, h), method=Image.LANCZOS,
                        centering=(cx, cy))


def enhance_thumb(im):
    """Deterministic lift for dark/low-contrast photos: brighten
    thumbs whose mean is under 100, gentle autocontrast, mild
    sharpening for all. Bright photos pass through almost
    untouched. Keeps every photo on the page readable at 52 px."""
    mean = ImageStat.Stat(im.convert("L")).mean[0]
    if mean < 100:
        im = ImageEnhance.Brightness(im).enhance(
            min(1.45, 105.0 / max(mean, 1)))
        im = ImageOps.autocontrast(im, cutoff=1)
    return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60,
                                             threshold=2))


def rounded_thumb(path, size, radius):
    """Square photo thumbnail with rounded corners (deterministic)."""
    im = Image.open(path).convert("RGB")
    im = ImageOps.fit(im, (size, size), method=Image.LANCZOS)
    im = enhance_thumb(im)
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius,
                         fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0))
    out.putalpha(mask)
    return out


# ---------------- stories (36 verified stories, all English) ----------------

HERO = ("TOP STORY  \u00b7  JUSTICE",
        "World Court: Myanmar committed genocide",
        "The ICJ rules 9\u20136 that Myanmar committed genocide against "
        "the Rohingya — the first time the court has found a state "
        "guilty of genocide.",
        "ICJ VOTE  9\u20136",
        "THE HAGUE  \u00b7  19 NOV")

# Dense list: (tag, headline, summary). Same 36 stories as v8/v9/v10;
# a few summaries trimmed a couple of words (facts unchanged) so
# every row fits the single 11 pt summary size with no truncation.
DENSE = [
    ("WEATHER", "Cyclone Akvan hits Odisha coast",
     "Landfall near Gopalpur, winds 70\u201380 km/h; 300,000 evacuated."),
    ("DIPLOMACY", "Trump, Xi & Putin meet in Shenzhen",
     "First three-way summit ends with a four-point peace "
     "declaration."),
    ("CONFLICT", "Three Kyiv bridges hit in missile attack",
     "Major Russian missile strike on Kyiv; debris hits a building "
     "in Obolonskyi."),
    ("TECH", "Anthropic soars on Nasdaq debut",
     "Shares close ~17% above the $83 IPO price, at about $97."),
    ("MARKETS", "Stocks slide for a fifth day",
     "S&P 500 \u22122%; Nikkei plunges 4.8% on AI-bubble fears."),
    ("CONFLICT", "Houthi missile hits Riyadh tower",
     "Missile damages the PIF tower in Riyadh's financial district."),
    ("CLIMATE", "COP31 ends in final-day deadlock",
     "Africa demands 3\u00d7 climate finance; Europe wants focus on "
     "old pledges."),
    ("DIPLOMACY", "Ukraine allies meet in Berlin",
     "Ukraine's allies: Europe is ready to negotiate with Russia."),
    ("CONFLICT", "Crimea Bridge hit a third time",
     "Third Ukrainian strike this week; Putin vows revenge."),
    ("SECURITY", "IAEA: North Korea expanding uranium enrichment",
     "UN atomic agency: Pyongyang is expanding uranium enrichment."),
    ("HEALTH", "Kenya beats Ebola",
     "Last Ebola patient discharged, 37 days after the first case."),
    ("GAMES", "GTA 6 launch tops $2.3B",
     "GTA 6 launch sales top $2.3 billion."),
    ("ECONOMY", "IMF: global debt nears 100% of world GDP",
     "Global public debt nears 100% of world GDP."),
    ("TECH", "Italy fines Meta \u20ac805M",
     "Fine for accessing Android photos without consent."),
    ("TRANSPORT", "FAA ground stop strands 1.5M travelers",
     "Ground stop strands 1.5 million travelers."),
    ("DEFENCE", "UK pledges 1,000+ drones for Ukraine",
     "\u00a3260M package of long-range drones."),
    ("POLITICS", "US Senate passes energy bill 62\u201333",
     "Faster energy permitting; heads to the House."),
    ("POLITICS", "Senate rejects Iran war-powers vote 51\u201348",
     "Iran war-powers resolution rejected."),
    ("POLITICS", "Trump pardons Pete Rose posthumously",
     "US baseball legend pardoned posthumously."),
    ("SECURITY", "Pakistan kills 22 militants",
     "Pakistani forces kill 22 militants near the Afghan border."),
    ("EUROPE", "UK and EU agree youth mobility scheme",
     "Youth mobility scheme agreed."),
    ("AFRICA", "Nigeria ends jail for attempted suicide",
     "Nigeria ends jail time for attempted suicide."),
    ("AFRICA", "Senegal boat capsizing kills four",
     "Migrant boat capsizes, four dead."),
    ("CULTURE", "Ella Langley sweeps CMA Awards",
     "Country star wins Entertainer of the Year."),
    ("EUROPE", "Poland probes unknown objects",
     "Poland probes unknown objects near the Ukraine border."),
    ("CONFLICT", "Israeli forces cross Gaza Yellow Line",
     "Israeli forces cross the ceasefire line in central Gaza."),
    ("CLIMATE", "COP31 draft drops fossil-fuel phase-out",
     "Draft deal drops the call to end fossil fuels."),
    ("SECURITY", "Iraq deploys forces near militia stronghold",
     "Federal forces deployed in Jurf al-Sakhar, a Kataib Hezbollah "
     "stronghold."),
    ("LATAM", "Bukele registers for third term",
     "El Salvador's president formally registers for a third term."),
    ("LATAM", "Argentina approves disability framework",
     "Argentine Senate approves permanent disability framework, "
     "71\u20130."),
    ("ASIA", "Nepal PM to make first state visit to India",
     "Balendra Shah visits New Delhi for bilateral talks."),
    ("DIPLOMACY", "Xi and Albanese hold talks in Shenzhen",
     "Xi pushes a trust-based partnership with Australia."),
    ("AFRICA", "Malawi fuel crisis triggers violence",
     "Fuel crisis sparks violence and economic strain."),
    ("TECH", "IEA: AI data centers may spike emissions",
     "IEA warns AI data centers could sharply raise emissions by "
     "2030."),
    ("TECH", "China-linked spies exploited VMware zero-day",
     "China-linked spies exploited a VMware flaw before it was "
     "patched."),
]

MX = 32                       # page margin
CW = W - 2 * MX                # 960 content width
GAP = 18                       # gap between the three dense columns
COLW = (CW - 2 * GAP) // 3     # 308 per column
ROWS = 12                      # 3 columns x 12 rows = 36 slots (1 hero + 35)
ROW_H = 62                     # tall enough for 2-line headline + 2-line summary
THUMB = 52                     # photo thumbnail size per dense row
THUMB_GAP = 8                  # gap between thumbnail and text


def main():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # ================= MASTHEAD =================
    f_mast = font(SERIF, 46)
    title = "THE WORLD TODAY"
    tw = tracked_width(d, title, f_mast, 6)
    draw_tracked(d, (W - tw) / 2, 4, title, f_mast, INK, 6)

    # Edition flanks in small tracked caps, vertically centred on
    # the title (only drawn when they clear the title with room).
    f_flank = font(SANS_BOLD, 11)
    flank_l = "WORLD EDITION"
    flank_r = "No. 324"
    lw = tracked_width(d, flank_l, f_flank, 2)
    rw2 = tracked_width(d, flank_r, f_flank, 2)
    if MX + lw + 30 < (W - tw) / 2 and (W + tw) / 2 + 30 < W - MX - rw2:
        draw_tracked(d, MX, 20, flank_l, f_flank, SLATE, 2)
        draw_tracked(d, W - MX - rw2, 20, flank_r, f_flank, SLATE, 2)

    f_date = font(SANS_BOLD, 15)
    f_meta = font(SANS, 15)
    draw_tracked(d, MX, 60, "FRIDAY, 20 NOVEMBER 2026", f_date, INK, 2)
    right = "36 STORIES \u00b7 6 CONTINENTS"
    rw = tracked_width(d, right, f_meta, 2)
    f_count = font(SANS_BOLD, 15)
    draw_tracked(d, W - MX - rw, 60, right, f_count, RED, 2)

    # Small gold diamond ornament centred on the dateline row.
    cx, cy = W // 2, 68
    d.polygon([(cx, cy - 5), (cx + 5, cy), (cx, cy + 5), (cx - 5, cy)],
              fill=GOLD)

    d.rectangle([MX, 78, W - MX, 80], fill=INK)
    d.rectangle([MX, 82, W - MX, 83], fill=RED)
    d.rectangle([MX, 85, W - MX, 86], fill=GOLD)

    # ================= HERO (108 px, dramatic editorial treatment) =================
    hy, hh = 88, 108
    hero = cover("hero-icj.jpg", W, hh, cy=0.62)
    hero = ImageEnhance.Color(hero).enhance(0.92)
    hero = ImageEnhance.Brightness(hero).enhance(0.97)
    hero = ImageEnhance.Contrast(hero).enhance(1.06)
    img.paste(hero, (0, hy))

    scrim = Image.new("RGBA", (W, hh), (8, 12, 18, 40))
    img.paste(scrim, (0, hy), scrim)
    grad = Image.new("RGBA", (W, hh), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(hh):
        a = int(252 * (i / (hh - 1)) ** 1.1)
        gd.line([(0, i), (W, i)], fill=(8, 12, 18, a))
    img.paste(grad, (0, hy), grad)
    d = ImageDraw.Draw(img)

    # vote chip, top right of the photo
    d.rectangle([836, hy + 8, 988, hy + 32], fill=CHIP, outline=GOLD,
                width=1)
    f_chip = font(SANS_BOLD, 14)
    chip_txt = HERO[3]
    cw = d.textlength(chip_txt, font=f_chip)
    d.text((912 - cw / 2, hy + 15), chip_txt, font=f_chip, fill=GOLD_LT)

    # kicker on a dark chip so gold stays readable over the photo
    f_kick = font(SANS_BOLD, 14)
    kw = tracked_width(d, HERO[0], f_kick, 3)
    d.rectangle([MX - 8, hy + 8, MX + kw + 8, hy + 32], fill=CHIP)
    draw_tracked(d, MX, hy + 14, HERO[0], f_kick, GOLD_LT, 3)
    f_hhead = font(SERIF, 28)
    d.text((MX, hy + 34), HERO[1], font=f_hhead, fill=WHITE)
    rule_y = hy + 68
    d.rectangle([MX, rule_y, MX + 44, rule_y + 3], fill=GOLD_LT)
    f_hbody = font(SERIF_IT, 13)
    blines = wrap(d, HERO[2], f_hbody, CW)
    draw_lines(d, blines, MX, rule_y + 8, f_hbody, WHITE_SOFT, 17)

    # dateline + illustration credit, bottom of the photo
    f_credit = font(SANS, 11)
    d.text((MX, hy + hh - 16), HERO[4], font=f_credit, fill=GOLD_LT)
    credit = "ILLUSTRATION \u00b7 PEACE PALACE, THE HAGUE"
    ctw = d.textlength(credit, font=f_credit)
    d.text((W - MX - ctw, hy + hh - 16), credit, font=f_credit,
           fill=WHITE_SOFT)

    # ================= SECTION HEADER =================
    sy = 206
    f_sec = font(SANS_BOLD, 14)
    d.rectangle([MX, sy + 4, MX + 7, sy + 11], fill=GOLD)
    draw_tracked(d, MX + 14, sy, "THE DAY IN BRIEF", f_sec, RED, 3)
    f_sec_r = font(SANS, 13)
    rlabel = "35 MORE STORIES"
    rw = d.textlength(rlabel, font=f_sec_r)
    d.text((W - MX - rw, sy + 1), rlabel, font=f_sec_r, fill=SLATE)
    d.rectangle([MX, sy + 24, W - MX, sy + 25], fill=INK)

    # ================= DENSE LIST: 3 columns x 12 rows, big photo thumbs =================
    # v12: ONE type scale for every row — 13.5 pt serif-bold headline
    # (red caps section kicker inline, FT style) and 10.5 pt sans
    # summary. Both wrap to at most 2 lines; the renderer asserts
    # the limits and the row height, so nothing is truncated and
    # nothing can overlap the next row.
    top = sy + 34                      # 240
    rows = ROWS
    row_h = ROW_H
    f_tag = font(SANS_BOLD, 10)
    f_head = font(SERIF, 13.5)
    f_sum = font(SANS, 10.5)
    tx_off = THUMB + THUMB_GAP         # text starts after the photo
    text_w = COLW - tx_off             # 248
    head_lh = 16
    sum_lh = 12.5
    text_top = 1                       # text block starts 1 px into the row
    gap_hs = 3                         # gap between headline and summary

    # Preload the 35 photo thumbnails (fail fast if one is missing).
    thumbs = []
    for idx in range(len(DENSE)):
        thumbs.append(rounded_thumb(
            os.path.join(THUMBS, f"{idx:02d}.jpg"), THUMB, 4))

    # vertical hairlines between the columns
    for sep in (1, 2):
        sx = MX + sep * COLW + (sep - 1) * GAP + GAP // 2
        d.rectangle([sx, top + 2, sx, top + rows * row_h - 6], fill=HAIR)

    max_block = 0
    for idx, (tag, head, summ) in enumerate(DENSE):
        col = idx // rows
        row = idx % rows
        x = MX + col * (COLW + GAP)
        y = top + row * row_h
        tx = x + tx_off                 # text starts after the photo

        # Photo thumbnail with a thin hairline frame, top-aligned
        # with the text block.
        img.paste(thumbs[idx], (x, y + 5), thumbs[idx])
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x, y + 5, x + THUMB - 1, y + 5 + THUMB - 1],
                            radius=4, outline=HAIR, width=1)

        # Headline: red caps kicker + serif-bold headline, wrapped
        # as one paragraph, at most 2 lines.
        hlines = wrap_mixed(d, [(tag, f_tag, RED), (head, f_head, INK)],
                            text_w)
        assert len(hlines) <= 2, f"headline too long: {head}"
        y_cur = draw_mixed(d, hlines, tx, y + text_top, head_lh)

        # Summary: at most 2 lines.
        slines = wrap(d, summ, f_sum, text_w)
        assert len(slines) <= 2, f"summary too long: {summ}"
        y_cur = draw_lines(d, slines, tx, y_cur + gap_hs, f_sum,
                           INK_SOFT, sum_lh)

        block = y_cur - y
        max_block = max(max_block, block)
        assert block <= row_h - 1, f"row overflow: {head} ({block}px)"

        if row < rows - 1:
            d.rectangle([x, y + row_h - 1, x + COLW, y + row_h],
                        fill=HAIR)

    print(f"dense rows: max text block {max_block}px of {row_h}px row, "
          f"0 truncated, 0 overflow")

    # ================= FOOTER =================
    d.rectangle([MX, 992, W - MX, 993], fill=HAIR)
    f_lab = font(SANS_BOLD, 12)
    draw_tracked(d, MX, 1000, "THE WORLD TODAY", f_lab, SLATE, 1)
    right_lab = "PAGE 1 OF 1"
    rw = tracked_width(d, right_lab, f_lab, 1)
    draw_tracked(d, W - MX - rw, 1000, right_lab, f_lab, SLATE, 1)
    f_foot = font(SANS, 13)
    msg = "Compiled from major wire reports  \u00b7  20 November 2026"
    tw = d.textlength(msg, font=f_foot)
    d.text(((W - tw) / 2, 999), msg, font=f_foot, fill=SLATE)

    img.save(OUT, "PNG", optimize=True)
    size = os.path.getsize(OUT)
    print(f"Wrote {OUT}: {img.size[0]}x{img.size[1]}, {size} bytes")
    if size > MAX_BYTES:
        q = img.convert("P", palette=Image.ADAPTIVE, colors=256,
                        dither=Image.FLOYDSTEINBERG)
        q.save(OUT, "PNG", optimize=True)
        size = os.path.getsize(OUT)
        print(f"Quantized to palette: {size} bytes")
    if size > MAX_BYTES:
        raise SystemExit(f"entry still too large: {size} bytes")


if __name__ == "__main__":
    main()
