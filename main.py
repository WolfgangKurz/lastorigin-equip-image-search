import sys
import os
import json

import cv2 as cv
import imutils
import numpy as np

VERBOSE = False
DEBUG = False

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "template")
OFFSET_THRESHOLD = 0.96
SIMMILAR_THRESHOLD = 0.6
SIMMILAR_NEAR_THRESHOLD = 10
TM_OFFSET = cv.TM_CCORR_NORMED
TM = cv.TM_CCOEFF_NORMED


def main(INPUT):
    if VERBOSE:
        print("equip-image-search")
        print("load templates...")

    equips: list[str] = []
    equip_files = [f for f in os.listdir(TEMPLATE_DIR) if f.startswith("UI_Icon_Equip_") and os.path.isfile(os.path.join(TEMPLATE_DIR, f))]

    t_x = int(np.ceil(np.sqrt(len(equip_files))))  # x cells
    t_y = int(np.ceil(len(equip_files) / t_x))  # y cells
    equip_grid = np.zeros((t_y * 100, t_x * 100, 3), np.uint8)  # grid image

    if VERBOSE:
        print(f"{len(equip_files)} templates to load, {t_x}x{t_y} grid prepared")

    for i in range(len(equip_files)):
        f = equip_files[i]
        fname = os.path.splitext(f)[0]
        img = cv.imread(os.path.join(TEMPLATE_DIR, f), cv.IMREAD_UNCHANGED)

        h, w, _ = img.shape
        if w != 128 or h != 128:  # not perfect icon
            img2 = np.zeros((128, 128, 4), np.uint8)
            x2, y2 = 64 - w // 2, 64 - h // 2
            img2[y2:y2+h, x2:x2+w] = img
            img = img2

        img = imutils.resize(img, width=100)

        alpha: cv.Mat = cv.split(img)[3]  # extract alpha
        alpha = alpha.astype(float) / 255.0  # normalize alpha to multiply
        alpha = alpha.repeat(3).reshape((100, 100, 3))

        img = cv.cvtColor(img, cv.COLOR_BGRA2BGR).astype(float)
        img: cv.Mat = cv.multiply(alpha, img)  # premultiplied alpha
        img = img.astype(np.uint8)

        # img[0:35, 0:35].fill(0)  # type and rarity
        # img[0:30, 50:100].fill(0)  # enchant

        x = (i % t_x) * 100
        y = (i // t_x) * 100
        equip_grid[y:y+100, x:x+100] = img

        equips.append(fname[14:])

    equip_grid = cv.cvtColor(equip_grid, cv.COLOR_BGR2GRAY)

    if VERBOSE:
        print(f"{len(equips)} templates loaded, {t_x}x{t_y} grid ready")
        print("finding scale value...")

    unequip = cv.imread(os.path.join(STATIC_DIR, "unequip.png"), cv.IMREAD_GRAYSCALE)
    unequip_left = cv.imread(os.path.join(STATIC_DIR, "unequip_left.png"), cv.IMREAD_GRAYSCALE)
    target = cv.imread(INPUT, cv.IMREAD_GRAYSCALE)  # INPUT

    # min_h, min_w = slot_template.shape
    min_h, min_w = 120, 498

    def mat2loc(res: cv.Mat, tm: int = None) -> tuple[int, int]:
        if tm is None:
            tm = TM

        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
        return min_loc if tm == cv.TM_SQDIFF or tm == cv.TM_SQDIFF_NORMED else max_loc

    # finding scale value
    sf = False  # scale found
    spi = None
    spm = None
    for sc in np.arange(0.5, 2.0, 0.05):
        scale = round(sc, 2)

        rh, rw = unequip.shape
        if rw * scale > min_w or rh * scale > min_h:  # too big
            continue

        resized = imutils.resize(unequip, width=int(unequip.shape[1] * scale))
        if DEBUG:
            cv.imwrite(f"debug/resize-{scale}.png", resized)

        res = cv.matchTemplate(target, resized, TM_OFFSET)
        min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)

        if max_val >= OFFSET_THRESHOLD:
            if spm is not None and spm > max_val:  # prev scale is more fit
                break

            spi = scale
            spm = max_val
            sf = True

    if not sf:
        ret = {
            "result": False,
            "message": "invalid screenshot, too small or too big",
        }
    else:
        if VERBOSE:
            print(f"found on scale {scale}")

        ret = {
            "result": True,
            "scale": float(spi),
            "data": [],
        }

        resized = imutils.resize(target, width=int(target.shape[1] * (1.0 / spi)))  # unequip icon scale = inverse of input scale

        uneq_res = cv.matchTemplate(resized, unequip, TM_OFFSET)
        uneq_loc = np.where(uneq_res >= OFFSET_THRESHOLD)
        uneq_loc = list(zip(*uneq_loc[::-1]))
        uneq_tb: list[tuple[int, int]] = []

        nth = 0
        for p_uneq in uneq_loc:  # find all unequip icons
            if any(np.abs(p[0] - p_uneq[0]) < SIMMILAR_NEAR_THRESHOLD and np.abs(p[1] - p_uneq[1]) < SIMMILAR_NEAR_THRESHOLD for p in uneq_tb):
                continue
            uneq_tb.append(p_uneq)

            nth += 1
            nth_src = resized[p_uneq[1]-80:p_uneq[1]+200, p_uneq[0]-550:p_uneq[0]+100]

            if DEBUG and not os.path.exists(f"debug/{nth}"):
                os.makedirs(f"debug/{nth}")

            res = cv.matchTemplate(nth_src, unequip_left, TM_OFFSET)  # unequip button left-side
            sl, sy = mat2loc(res, TM_OFFSET)
            sx = sl - 498

            if DEBUG:
                resized2 = cv.cvtColor(nth_src, cv.COLOR_GRAY2BGR)
                cv.rectangle(resized2, p_uneq, (p_uneq[0]+unequip.shape[1], p_uneq[1]+unequip.shape[0]), (0, 0, 255), 2)
                cv.rectangle(resized2, (sl, sy), (sl+unequip_left.shape[1], sy+unequip_left.shape[0]), (255, 0, 0), 2)
                cv.rectangle(resized2, (sx, sy), (sx+min_w, sy+min_h), (0, 255, 0), 2)
                cv.imwrite(f"debug/{nth}/resized.png", resized2)

            crop = nth_src[sy:sy+min_h, sx:sx+min_w]  # equip slot area
            if DEBUG:
                cv.imwrite(f"debug/{nth}/slots.png", crop)

            if VERBOSE:
                print("cropping slots...")

            slots = []
            w = min_w
            for i in range(4):
                x = 10 + int(w / 4 * i)

                slot = crop[10:110, x:x+100]
                # slot[0:35, 0:35].fill(0)  # type and rarity
                # slot[0:30, 50:100].fill(0)  # enchant

                slots.append(slot)

            if VERBOSE:
                print("matching...")

            ret_mat = {
                "parsed": {
                    "x": int(p_uneq[0] - 550 + sx),
                    "y": int(p_uneq[1] - 80 + sy),
                    "w": min_w,
                    "h": min_h,
                },
                "score": [],
                "matched": [],
            }
            for i in range(len(slots)):
                slot = slots[i]

                res = cv.matchTemplate(equip_grid, slot, TM)
                min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)

                if TM == cv.TM_SQDIFF or TM == cv.TM_SQDIFF_NORMED:
                    x, y = min_loc
                else:
                    x, y = max_loc

                if DEBUG:
                    equip_grid2 = cv.cvtColor(equip_grid, cv.COLOR_GRAY2BGR)

                o_x, o_y = x, y
                x = int(np.round(x / 100))
                y = int(np.round(y / 100))

                idx = x + y * t_x
                eq = equips[idx]
                if eq.startswith("PLACEHOLDER_"):
                    eq = None

                if DEBUG:
                    loc = np.where(res >= SIMMILAR_THRESHOLD)
                    loc = list(zip(*loc[::-1]))
                    tb = []

                    if len(loc) == 0:  # bad quality, pick best, should same with matched one
                        pass
                    else:
                        for pt in loc:
                            if any(np.abs(p[0] - pt[0]) < SIMMILAR_NEAR_THRESHOLD and np.abs(p[1] - pt[1]) < SIMMILAR_NEAR_THRESHOLD for p in tb):
                                continue

                            cv.rectangle(equip_grid2, pt, (pt[0]+100, pt[1]+100), (255, 0, 0), 2)
                            tb.append(pt)

                            if len(tb) > 100:  # too many
                                break

                    if VERBOSE:
                        print(f"{i} : {equips[idx]} [{x}, {y}]      simmilar {len(tb)} (or more) items")
                elif VERBOSE:
                    print(f"{i} : {eq}")

                ret_mat["matched"].append(eq)
                ret_mat["score"].append(float(max_val))

                if DEBUG:
                    cv.rectangle(equip_grid2, (o_x, o_y), (o_x+100, o_y+100), (0, 0, 255), 2)

                    cv.imwrite(f"debug/{nth}/slot{i+1}.png", slot)
                    cv.imwrite(f"debug/{nth}/grid{i+1}.png", equip_grid2)

            ret["data"].append(ret_mat)

    print(json.dumps(ret, ensure_ascii=False))  # , indent=4))

# INPUT = "test8.png"


if __name__ == "__main__":
    try:
        if len(sys.argv) >= 2:
            input = sys.argv[1]
            main(input)
        else:
            raise Exception("not enough parameters")
    except:
        ret = {
            "result": False,
            "message": "Unexpected error, maybe not readable image file",
        }
        print(json.dumps(ret, ensure_ascii=False))
