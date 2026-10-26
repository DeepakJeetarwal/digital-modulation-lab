
"""
Validation tests for the Digital Modulation Lab.

Checks:
1. Noise-free bit recovery.
2. Average constellation energy.
3. BER behaviour across different Eb/N0 values.
4. Reproducibility of the AWGN channel.
"""

import numpy as np

from src.modulation import SUPPORTED_SCHEMES, modulate, demodulate
from src.channel import add_awgn


NUM_BITS = 120_000
SNR_VALUES = [0, 5, 8, 10, 12, 15, 20]
ENERGY_TOLERANCE = 0.01

BITS_PER_SYMBOL = {
    "BPSK": 1,
    "QPSK": 2,
    "8-PSK": 3,
    "16-QAM": 4,
}


def validate_scheme(scheme):
    """Validate modulation, demodulation, energy, and BER behaviour."""

    k = BITS_PER_SYMBOL[scheme]
    usable_bits = (NUM_BITS // k) * k

    rng = np.random.default_rng(42)

    bits = rng.integers(
        0, 2, size=usable_bits, dtype=np.uint8
    )

    # Modulation and average energy.
    tx = modulate(bits, scheme)
    measured_energy = float(np.mean(np.abs(tx) ** 2))

    # Theoretical constellation energy is one.
    # A random finite sequence can differ slightly from this value.
    assert abs(measured_energy - 1.0) < ENERGY_TOLERANCE, (
        f"{scheme}: unexpected average symbol energy "
        f"{measured_energy:.6f}"
    )

    # Perfect recovery without noise.
    recovered_clean = demodulate(tx, scheme)
    clean_errors = int(np.count_nonzero(bits != recovered_clean))

    assert clean_errors == 0, (
        f"{scheme}: {clean_errors} errors without noise"
    )

    # Measure BER for each SNR.
    measurements = []

    for snr in SNR_VALUES:
        rx = add_awgn(
            tx,
            snr,
            scheme,
            rng=np.random.default_rng(1000 + snr),
        )

        recovered = demodulate(rx, scheme)
        errors = int(np.count_nonzero(bits != recovered))
        ber = errors / usable_bits

        measurements.append({
            "snr": snr,
            "errors": errors,
            "ber": ber,
        })

    # Reproducibility check.
    rx_a = add_awgn(
        tx[:100],
        8,
        scheme,
        rng=np.random.default_rng(123),
    )
    rx_b = add_awgn(
        tx[:100],
        8,
        scheme,
        rng=np.random.default_rng(123),
    )

    assert np.allclose(rx_a, rx_b), (
        f"{scheme}: seeded noise is not reproducible"
    )

    # Report results.
    print(f"\n{scheme}")
    print("-" * 58)
    print(f"Average symbol energy: {measured_energy:.6f}")
    print(f"Errors without noise:  {clean_errors}")
    print(f"{'Eb/N0':>8} {'Errors':>12} {'Measured BER':>18}")

    for result in measurements:
        print(
            f"{result['snr']:>5} dB "
            f"{result['errors']:>10} "
            f"{result['ber']:>18.6e}"
        )

    # At the lowest and highest tested SNRs, BER should normally
    # decrease. Individual adjacent measurements may fluctuate.
    low_ber = measurements[0]["ber"]
    high_ber = measurements[-1]["ber"]

    assert high_ber <= low_ber, (
        f"{scheme}: BER did not decrease between "
        f"{SNR_VALUES[0]} and {SNR_VALUES[-1]} dB"
    )

    return measurements


def main():
    print("DIGITAL MODULATION VALIDATION")
    print("=" * 58)

    for scheme in SUPPORTED_SCHEMES:
        validate_scheme(scheme)

    print("\nAll structural and reproducibility checks passed.")
    print(
        "Note: finite-sample BER values fluctuate; "
        "zero observed errors do not prove zero theoretical BER."
    )


if __name__ == "__main__":
    main()
