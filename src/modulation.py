
"""
Digital modulation and demodulation functions.

Supported schemes:
    BPSK, QPSK, 8-PSK, 16-QAM
"""

import numpy as np


SUPPORTED_SCHEMES = ("BPSK", "QPSK", "8-PSK", "16-QAM")


def bits_per_symbol(scheme: str) -> int:
    """Return the number of bits encoded in each symbol."""
    mapping = {
        "BPSK": 1,
        "QPSK": 2,
        "8-PSK": 3,
        "16-QAM": 4,
    }

    if scheme not in mapping:
        raise ValueError(f"Unsupported modulation scheme: {scheme}")

    return mapping[scheme]


def _gray_to_binary(gray: int) -> int:
    """Convert a Gray-coded integer to its binary integer."""
    binary = gray

    while gray:
        gray >>= 1
        binary ^= gray

    return binary


def _constellation(scheme: str):
    """
    Return normalized constellation points and their corresponding
    bit labels. Each row in labels identifies the bits for one point.
    """
    if scheme == "BPSK":
        points = np.array([1 + 0j, -1 + 0j])
        labels = np.array([[0], [1]], dtype=np.uint8)

    elif scheme == "QPSK":
        # Gray-coded phase order: 00, 01, 11, 10
        gray_labels = [(0, 0), (0, 1), (1, 1), (1, 0)]
        phases = np.pi / 4 + np.arange(4) * np.pi / 2
        points = np.exp(1j * phases)
        labels = np.array(gray_labels, dtype=np.uint8)

    elif scheme == "8-PSK":
        # Gray-coded phase order around the constellation.
        phases = 2 * np.pi * np.arange(8) / 8
        points = np.exp(1j * phases)

        labels = []
        for phase_index in range(8):
            gray = phase_index ^ (phase_index >> 1)
            labels.append([
                (gray >> 2) & 1,
                (gray >> 1) & 1,
                gray & 1,
            ])

        labels = np.array(labels, dtype=np.uint8)

    elif scheme == "16-QAM":
        # Gray-coded 4-PAM levels on each axis:
        # 00 -> -3, 01 -> -1, 11 -> +1, 10 -> +3
        axis_levels = [-3, -1, 1, 3]
        axis_bits = [(0, 0), (0, 1), (1, 1), (1, 0)]

        points = []
        labels = []

        for i, inphase in enumerate(axis_levels):
            for q, quadrature in enumerate(axis_levels):
                points.append(inphase + 1j * quadrature)
                labels.append(axis_bits[i] + axis_bits[q])

        # Average symbol energy becomes one.
        points = np.array(points, dtype=complex) / np.sqrt(10)
        labels = np.array(labels, dtype=np.uint8)

    else:
        raise ValueError(f"Unsupported modulation scheme: {scheme}")

    return points, labels


def modulate(bits: np.ndarray, scheme: str) -> np.ndarray:
    """
    Convert a one-dimensional binary array into complex symbols.
    """
    bits = np.asarray(bits, dtype=np.uint8)

    if bits.ndim != 1 or not np.all((bits == 0) | (bits == 1)):
        raise ValueError("bits must be a one-dimensional binary array")

    k = bits_per_symbol(scheme)

    if len(bits) == 0 or len(bits) % k != 0:
        raise ValueError(
            f"The number of bits must be a positive multiple of {k} "
            f"for {scheme}."
        )

    points, labels = _constellation(scheme)
    groups = bits.reshape(-1, k)

    # Match each group to its constellation point.
    matches = np.all(
        groups[:, None, :] == labels[None, :, :],
        axis=2,
    )

    symbol_indices = np.argmax(matches, axis=1)

    return points[symbol_indices]


def demodulate(symbols: np.ndarray, scheme: str) -> np.ndarray:
    """
    Recover bits by choosing the nearest constellation point.
    """
    symbols = np.asarray(symbols, dtype=complex)

    if symbols.ndim != 1 or len(symbols) == 0:
        raise ValueError("symbols must be a non-empty one-dimensional array")

    points, labels = _constellation(scheme)

    # Squared Euclidean distance from each received symbol to each
    # possible transmitted constellation point.
    distances = np.abs(symbols[:, None] - points[None, :]) ** 2

    nearest_indices = np.argmin(distances, axis=1)

    return labels[nearest_indices].reshape(-1).astype(np.uint8)
