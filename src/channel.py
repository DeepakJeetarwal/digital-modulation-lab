
"""
AWGN channel for digital communication simulations.

The channel adds complex Gaussian noise to transmitted symbols.
SNR is controlled using Eb/N0, the energy per bit to noise
power spectral density ratio.
"""

import numpy as np

from src.modulation import bits_per_symbol


def add_awgn(
    symbols: np.ndarray,
    ebn0_db: float,
    scheme: str,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    Add complex AWGN to modulation symbols.

    Assumptions:
        - Ideal coherent detection
        - Complex baseband representation
        - Average symbol energy normalized to 1
        - Eb/N0 is specified in dB

    Parameters
    ----------
    symbols : np.ndarray
        Transmitted complex modulation symbols.
    ebn0_db : float
        Energy per bit to noise PSD ratio in dB.
    scheme : str
        BPSK, QPSK, 8-PSK, or 16-QAM.
    rng : np.random.Generator, optional
        Random generator for reproducible results.

    Returns
    -------
    np.ndarray
        Received symbols after AWGN is added.
    """
    symbols = np.asarray(symbols, dtype=complex)

    if symbols.ndim != 1 or symbols.size == 0:
        raise ValueError("symbols must be a non-empty 1D array")

    if not np.isfinite(ebn0_db):
        raise ValueError("Eb/N0 must be a finite number")

    k = bits_per_symbol(scheme)

    # Convert Eb/N0 from decibels to a linear ratio.
    ebn0_linear = 10 ** (ebn0_db / 10)

    # Average symbol energy is 1 for our normalized constellations.
    # Eb = Es / k, therefore N0 = Es / (k * Eb/N0).
    noise_variance = 1.0 / (k * ebn0_linear)

    # Each real component has variance N0/2.
    noise_std = np.sqrt(noise_variance / 2)

    if rng is None:
        rng = np.random.default_rng()

    noise = noise_std * (
        rng.standard_normal(symbols.size)
        + 1j * rng.standard_normal(symbols.size)
    )

    return symbols + noise
