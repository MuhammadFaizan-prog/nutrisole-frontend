"""Deterministic phone-camera corruptions for the robustness sweep (BGR uint8 in/out)."""
import cv2
import numpy as np


def tube_light(im):
    """Cool-white fluorescent cast: green up, red down (WB shift)."""
    f = im.astype(np.float32) * np.array([1.05, 1.12, 0.82], np.float32)  # B, G, R gains
    return np.clip(f, 0, 255).astype(np.uint8)


def sodium_lamp(im):
    """Night-stall sodium/incandescent cast: orange, blue suppressed."""
    f = im.astype(np.float32) * np.array([0.65, 0.95, 1.18], np.float32)
    return np.clip(f, 0, 255).astype(np.uint8)


def low_light(im):
    """~-1.5 EV with gamma and sensor noise."""
    f = (im.astype(np.float32) / 255.0) ** 1.2 * 0.35 * 255.0
    f += np.random.default_rng(0).normal(0, 4, im.shape)
    return np.clip(f, 0, 255).astype(np.uint8)


def motion_blur(im):
    k = max(5, int(round(min(im.shape[:2]) * 0.025)) | 1)
    kern = np.zeros((k, k), np.float32)
    kern[k // 2, :] = 1.0 / k
    return cv2.filter2D(im, -1, kern)


def jpeg40(im):
    ok, b = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 40])
    return cv2.imdecode(b, cv2.IMREAD_COLOR)


CORRUPTIONS = {"tube_light_wb": tube_light, "sodium_wb": sodium_lamp, "low_light": low_light, "motion_blur": motion_blur, "jpeg40": jpeg40}


def low_light_hard(im):
    """G2 held-out variant, OUTSIDE the G2 training augmentation family: ~-2 EV (gain .25),
    gamma 1.6, per-channel (chroma) sensor noise sigma 7, then JPEG 70 (night stall bulb)."""
    f = (im.astype(np.float32) / 255.0) ** 1.6 * 0.25 * 255.0
    f += np.random.default_rng(1).normal(0, 7, im.shape)
    ok, b = cv2.imencode(".jpg", np.clip(f, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 70])
    return cv2.imdecode(b, cv2.IMREAD_COLOR)


CORRUPTIONS["low_light_hard"] = low_light_hard


def tube_light_hard(im):
    """G3 held-out variant, OUTSIDE the G3 tube-light training family: strong cool-white cast
    (B 1.15, G 1.25, R 0.68), -0.5 EV, and 100 Hz flicker banding (horizontal sinusoid, 12% depth)."""
    f = im.astype(np.float32) * np.array([1.15, 1.25, 0.68], np.float32) * 0.72
    rows = np.arange(im.shape[0], dtype=np.float32)
    f *= (1.0 + 0.12 * np.sin(rows / max(1.0, im.shape[0] / 9.0) * 2 * np.pi))[:, None, None]
    return np.clip(f, 0, 255).astype(np.uint8)


CORRUPTIONS["tube_light_hard"] = tube_light_hard


def night_sodium_hard(im):
    """G4 held-out variant, OUTSIDE the G4 night training family: sodium-vapour cast (B .55, G .9, R 1.3),
    gain .18, gamma 2.2, chroma noise sigma 9, horizontal motion blur (hand shake), JPEG 60."""
    f = np.clip(im.astype(np.float32) * np.array([0.55, 0.9, 1.3], np.float32), 0, 255)
    f = (f / 255.0) ** 2.2 * 0.18 * 255.0
    f += np.random.default_rng(2).normal(0, 9, im.shape)
    f = np.clip(f, 0, 255).astype(np.uint8)
    k = max(5, int(round(min(im.shape[:2]) * 0.02)) | 1)
    kern = np.zeros((k, k), np.float32)
    kern[k // 2, :] = 1.0 / k
    ok, b = cv2.imencode(".jpg", cv2.filter2D(f, -1, kern), [cv2.IMWRITE_JPEG_QUALITY, 60])
    return cv2.imdecode(b, cv2.IMREAD_COLOR)


CORRUPTIONS["night_sodium_hard"] = night_sodium_hard
