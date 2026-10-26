
"""
Visualization of BER versus Eb/N0 for digital modulation schemes.
"""

import numpy as np
import matplotlib.pyplot as plt

from src.simulation import run_comparison


def plot_ber_comparison(results):
    fig, ax = plt.subplots(figsize=(11, 7))

    styles = {
        "BPSK": ("o", "#2563EB"),
        "QPSK": ("s", "#16A34A"),
        "8-PSK": ("^", "#EA580C"),
        "16-QAM": ("D", "#9333EA"),
    }

    for scheme, result in results.items():
        snr = result["ebn0_db"]
        ber = result["ber"]
        marker, color = styles[scheme]

        # Zero observed errors cannot be shown on a log scale.
        # Omit those points rather than plotting an artificial BER.
        valid = ber > 0

        ax.semilogy(
            snr[valid],
            ber[valid],
            marker=marker,
            color=color,
            linewidth=2,
            markersize=7,
            label=scheme,
        )

    ax.set_title(
        "Effect of SNR Variation on Digital Modulation Schemes",
        fontsize=15,
        fontweight="bold",
        pad=18,
    )

    ax.set_xlabel("Eb/N0 (dB)", fontsize=12)
    ax.set_ylabel("Bit Error Rate (BER)", fontsize=12)

    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend(title="Modulation Scheme")
    ax.set_xlim(0, 20)
    ax.set_ylim(1e-6, 1)

    fig.tight_layout()
    fig.savefig("ber_comparison.png", dpi=300, bbox_inches="tight")

    plt.show()


if __name__ == "__main__":
    snr_values = np.arange(0, 21, 1)

    results = run_comparison(
        ebn0_db_values=snr_values,
        num_bits=120000,
        seed=42,
    )

    plot_ber_comparison(results)
