
"""
Main simulation engine for comparing digital modulation schemes.

Measures bit error rate (BER) at different Eb/N0 values
for BPSK, QPSK, 8-PSK, and 16-QAM over an AWGN channel.
"""

import numpy as np

from src.modulation import (
    SUPPORTED_SCHEMES,
    modulate,
    demodulate,
    bits_per_symbol,
)
from src.channel import add_awgn


def simulate_ber(
    scheme: str,
    ebn0_db_values,
    num_bits: int = 60000,
    seed: int = 42,
) -> dict:
    """
    Simulate BER for one modulation scheme across Eb/N0 values.

    Returns:
        scheme: modulation scheme name
        ebn0_db: SNR values in dB
        ber: measured bit error rates
        errors: number of incorrectly recovered bits
        total_bits: number of transmitted bits per SNR value
    """

    if scheme not in SUPPORTED_SCHEMES:
        raise ValueError(f"Unsupported modulation scheme: {scheme}")

    if (
        isinstance(num_bits, bool)
        or not isinstance(num_bits, (int, np.integer))
        or num_bits <= 0
    ):
        raise ValueError("num_bits must be a positive integer")

    ebn0_db_values = np.asarray(ebn0_db_values, dtype=float)

    if (
        ebn0_db_values.ndim != 1
        or ebn0_db_values.size == 0
        or not np.all(np.isfinite(ebn0_db_values))
    ):
        raise ValueError(
            "Eb/N0 values must be a non-empty finite one-dimensional array"
        )

    k = bits_per_symbol(scheme)
    actual_num_bits = (num_bits // k) * k

    if actual_num_bits == 0:
        raise ValueError(
            f"num_bits must be at least {k} for {scheme}"
        )

    # Generate one reproducible transmitted sequence.
    bit_rng = np.random.default_rng(seed)

    transmitted_bits = bit_rng.integers(
        0,
        2,
        size=actual_num_bits,
        dtype=np.uint8,
    )

    transmitted_symbols = modulate(transmitted_bits, scheme)

    ber_values = []
    error_counts = []

    # Independent, reproducible noise at each SNR.
    # This prevents one SNR's noise generation from affecting another.
    seed_sequence = np.random.SeedSequence(seed)
    child_sequences = seed_sequence.spawn(len(ebn0_db_values))

    for ebn0_db, child_seed in zip(
        ebn0_db_values,
        child_sequences,
    ):
        noise_rng = np.random.default_rng(child_seed)

        received_symbols = add_awgn(
            transmitted_symbols,
            float(ebn0_db),
            scheme,
            rng=noise_rng,
        )

        recovered_bits = demodulate(
            received_symbols,
            scheme,
        )

        errors = int(
            np.count_nonzero(
                transmitted_bits != recovered_bits
            )
        )

        ber = errors / actual_num_bits

        error_counts.append(errors)
        ber_values.append(ber)

    return {
        "scheme": scheme,
        "ebn0_db": ebn0_db_values.copy(),
        "ber": np.asarray(ber_values, dtype=float),
        "errors": np.asarray(error_counts, dtype=int),
        "total_bits": actual_num_bits,
    }


def run_comparison(
    schemes=None,
    ebn0_db_values=None,
    num_bits: int = 60000,
    seed: int = 42,
) -> dict:
    """
    Run BER simulations for multiple modulation schemes.

    Each scheme uses the same base seed for reproducibility.
    """

    if schemes is None:
        schemes = list(SUPPORTED_SCHEMES)
    else:
        schemes = list(schemes)

    if not schemes:
        raise ValueError("Select at least one modulation scheme")

    if len(set(schemes)) != len(schemes):
        raise ValueError("Duplicate modulation schemes are not allowed")

    invalid_schemes = [
        scheme for scheme in schemes
        if scheme not in SUPPORTED_SCHEMES
    ]

    if invalid_schemes:
        raise ValueError(
            f"Unsupported modulation schemes: {invalid_schemes}"
        )

    if ebn0_db_values is None:
        ebn0_db_values = np.arange(0, 21, 2)

    ebn0_db_values = np.asarray(
        ebn0_db_values,
        dtype=float,
    )

    if (
        ebn0_db_values.ndim != 1
        or ebn0_db_values.size == 0
        or not np.all(np.isfinite(ebn0_db_values))
    ):
        raise ValueError(
            "Eb/N0 values must be a non-empty finite array"
        )

    results = {}

    for scheme in schemes:
        print(f"Simulating {scheme}...")

        results[scheme] = simulate_ber(
            scheme=scheme,
            ebn0_db_values=ebn0_db_values,
            num_bits=num_bits,
            seed=seed,
        )

    return results


def print_results(results: dict) -> None:
    """Print simulation results in a readable table."""

    print("\n" + "=" * 62)
    print(" DIGITAL MODULATION: BER vs. Eb/N0")
    print("=" * 62)

    for scheme, result in results.items():
        print(f"\n{scheme}")
        print("-" * 46)
        print(
            f"{'Eb/N0 (dB)':>12} "
            f"{'Errors':>12} "
            f"{'Total bits':>12} "
            f"{'BER':>12}"
        )

        for snr, errors, total_bits, ber in zip(
            result["ebn0_db"],
            result["errors"],
            [result["total_bits"]] * len(result["errors"]),
            result["ber"],
        ):
            print(
                f"{snr:12.1f} "
                f"{errors:12d} "
                f"{total_bits:12d} "
                f"{ber:12.6g}"
            )


if __name__ == "__main__":
    snr_values = np.arange(0, 21, 2)

    results = run_comparison(
        ebn0_db_values=snr_values,
        num_bits=60000,
        seed=42,
    )

    print_results(results)
