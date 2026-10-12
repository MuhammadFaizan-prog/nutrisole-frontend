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
