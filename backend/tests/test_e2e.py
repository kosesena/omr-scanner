"""End-to-end test: synthetic form with inverse-warp bubble placement."""
import cv2
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.omr_engine import OMREngine, FORM_CONFIG, ANSWER_LAYOUTS

def create_test_image(num_questions=20, seed=42):
    h, w = 1414, 1000
    img = np.ones((h, w, 3), dtype=np.uint8) * 240

    # ArUco markers
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    ms, mg = 60, 30
    for mid, (mx, my) in {0:(mg,mg),1:(w-mg-ms,mg),2:(mg,h-mg-ms),3:(w-mg-ms,h-mg-ms)}.items():
        m = cv2.aruco.generateImageMarker(aruco_dict, mid, ms)
        img[my:my+ms, mx:mx+ms] = cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)

    # Get inverse warp matrix
    engine = OMREngine(num_questions=num_questions)
    markers = engine.detect_markers(img)
    src_pts = np.float32([markers[i]["center"] for i in [0,1,2,3]])
    dst_pts = np.float32([[30,30],[970,30],[30,1384],[970,1384]])
    M_inv = cv2.getPerspectiveTransform(dst_pts, src_pts)

    def warped_to_orig(wx, wy):
        pt = cv2.perspectiveTransform(np.float32([[[wx, wy]]]), M_inv)
        return int(pt[0][0][0]), int(pt[0][0][1])

    # --- Student ID ---
    cfg = FORM_CONFIG["student_id"]
    y1w, y2w = h * cfg["top"], h * cfg["bottom"]
    x1w, x2w = w * cfg["left"], w * cfg["right"]
    cw = (x2w - x1w) / 10
    ch = (y2w - y1w) / 10
    bubble_r = int(min(cw, ch) * 0.33)

    student_id = "2024001337"
    for col, digit in enumerate(student_id):
        for row in range(10):
            wcx = x1w + (col + 0.5) * cw
            wcy = y1w + (row + 0.5) * ch
            ox, oy = warped_to_orig(wcx, wcy)
            if str(row) == digit:
                cv2.circle(img, (ox, oy), bubble_r, (20, 20, 20), -1)
            else:
                cv2.circle(img, (ox, oy), bubble_r, (190, 190, 190), 1)

    # --- Answers ---
    lk = min(ANSWER_LAYOUTS.keys(), key=lambda k: abs(k - num_questions))
    layout = ANSWER_LAYOUTS[lk]
    cols = layout["columns"]
    qpc = (num_questions + cols - 1) // cols
    options = ["A", "B", "C", "D", "E"]

    ay1, ay2 = h * layout["top"], h * layout["bottom"]
    ax1, ax2 = w * layout["left"], w * layout["right"]
    col_w = (ax2 - ax1) / cols

    answer_key = {str(q): options[(q-1) % 5] for q in range(1, num_questions+1)}
    np.random.seed(seed)
    student_answers = {}
    for q in range(1, num_questions+1):
        if np.random.random() < 0.85:
            student_answers[q] = answer_key[str(q)]
        else:
            wrong = [o for o in options if o != answer_key[str(q)]]
            student_answers[q] = np.random.choice(wrong)

    for ci in range(cols):
        bx1 = ax1 + ci * col_w + col_w * 0.2
        bx2 = ax1 + ci * col_w + col_w * 0.98
        bcw = (bx2 - bx1) / 5
        rh = (ay2 - ay1) / qpc
        br = int(min(bcw, rh) * 0.30)

        for row in range(qpc):
            qn = ci * qpc + row + 1
            if qn > num_questions: break
            chosen_idx = options.index(student_answers[qn])
            for oi in range(5):
                wcx = bx1 + (oi + 0.5) * bcw
                wcy = ay1 + (row + 0.5) * rh
                ox, oy = warped_to_orig(wcx, wcy)
                if oi == chosen_idx:
                    cv2.circle(img, (ox, oy), br, (20, 20, 20), -1)
                else:
                    cv2.circle(img, (ox, oy), br, (190, 190, 190), 1)

    return img, student_answers, answer_key, student_id

def add_camera_effects(img):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), 2.5, 0.97)
    out = cv2.warpAffine(img, M, (w, h), borderValue=(235, 235, 235))
    pts1 = np.float32([[0,0],[w,0],[0,h],[w,h]])
    pts2 = np.float32([[12,6],[w-6,10],[6,h-12],[w-10,h-6]])
    out = cv2.warpPerspective(out, cv2.getPerspectiveTransform(pts1, pts2), (w, h), borderValue=(235,235,235))
    noise = np.random.normal(0, 3, out.shape).astype(np.int16)
    out = np.clip(out.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(out, (3,3), 0)

def evaluate(result, expected_answers, expected_id, label):
    print(f"\n  [{label}]")
    if not result.success:
        print(f"  ❌ Error: {result.error}"); return False

    id_ok = sum(a == b for a, b in zip(result.student_id, expected_id))
    print(f"  Student ID: {result.student_id} ({id_ok}/{len(expected_id)} correct)")

    reads = sum(1 for q, a in expected_answers.items() if result.answers.get(q, "").upper() == a.upper())
    total = len(expected_answers)
    acc = reads / total * 100
    print(f"  Read accuracy: {acc:.1f}% ({reads}/{total})")
    if result.score is not None:
        print(f"  Score: {result.score:.1f}% ({result.correct_count}/{result.total_questions})")
    print(f"  Confidence: {result.confidence:.2f}")
    if result.unmarked: print(f"  Unmarked ({len(result.unmarked)}): {result.unmarked[:10]}")
    if result.multiple_marks: print(f"  Multi-mark ({len(result.multiple_marks)}): {result.multiple_marks[:10]}")

    passed = acc >= 75
    print(f"  {'✅ PASS' if passed else '❌ FAIL'}")
    return passed

def main():
    print("=" * 60)
    print("  OMR Scanner — End-to-End Test")
    print("=" * 60)
    ok = True

    for nq in [20, 40]:
        print(f"\n{'─'*60}\n  {nq}-question form\n{'─'*60}")
        img, ans, key, sid = create_test_image(nq)
        cv2.imwrite(f"/tmp/test_{nq}q_clean.png", img)
        engine = OMREngine(num_questions=nq)

        r1 = engine.scan(img, answer_key=key)
        ok &= evaluate(r1, ans, sid, "Clean")

        distorted = add_camera_effects(img)
        cv2.imwrite(f"/tmp/test_{nq}q_distorted.png", distorted)
        r2 = engine.scan(distorted, answer_key=key)
        ok &= evaluate(r2, ans, sid, "Camera sim")

    print(f"\n{'='*60}")
    print(f"  {'🎉 ALL TESTS PASSED!' if ok else '⚠️  NEEDS WORK'}")
    print(f"{'='*60}")
    return ok

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
