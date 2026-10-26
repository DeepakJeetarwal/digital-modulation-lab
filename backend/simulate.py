
"""JSON bridge between Electron and the Python simulation engine."""

import io
import json
import os
import sys
from contextlib import redirect_stdout

import numpy as np


# ---------------------------------------------------------
# PROJECT PATH CONFIGURATION
# ---------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Import the existing simulation engine.
from src.modulation import SUPPORTED_SCHEMES, modulate, demodulate
from src.channel import add_awgn
from src.simulation import run_comparison


# ---------------------------------------------------------
# SIMULATION REQUEST HANDLER
# ---------------------------------------------------------

def run_request(request):
    """Run the requested modulation experiment and return JSON data."""

    schemes = request.get("schemes", list(SUPPORTED_SCHEMES))
    scheme = request.get("scheme", "BPSK")
    snr = int(request.get("snr", 8))
    num_bits = int(request.get("num_bits", 30000))
    seed = int(request.get("seed", 42))

    # Validate modulation schemes.
    if not schemes or any(s not in SUPPORTED_SCHEMES for s in schemes):
        raise ValueError("Select valid modulation schemes.")

    if scheme not in schemes:
        scheme = schemes[0]

    # Validate simulation parameters.
    if not 0 <= snr <= 20:
        raise ValueError("SNR must be between 0 and 20 dB.")

    if not 12000 <= num_bits <= 120000:
        raise ValueError(
            "Bit count must be between 12,000 and 120,000."
        )

    # -----------------------------------------------------
    # BER COMPARISON OVER THE SNR RANGE
    # -----------------------------------------------------

    snr_values = np.arange(0, 21, 2)

    # Suppress progress messages so stdout contains only JSON.
    with redirect_stdout(io.StringIO()):
        comparison = run_comparison(
            schemes=schemes,
            ebn0_db_values=snr_values,
            num_bits=num_bits,
            seed=seed,
        )

    # -----------------------------------------------------
    # GENERATE SELECTED SCHEME AT SELECTED SNR
    # -----------------------------------------------------

    bits_per_symbol = {
        "BPSK": 1,
        "QPSK": 2,
        "8-PSK": 3,
        "16-QAM": 4,
    }

    k = bits_per_symbol[scheme]

    rng = np.random.default_rng(seed)
    usable_bits = (num_bits // k) * k

    bits = rng.integers(
        0, 2, size=usable_bits, dtype=np.uint8
    )

    tx_symbols = modulate(bits, scheme)

    rx_symbols = add_awgn(
        tx_symbols,
        snr,
        scheme,
        rng=rng,
    )

    rx_bits = demodulate(rx_symbols, scheme)

    errors = int(np.count_nonzero(bits != rx_bits))
    measured_ber = errors / usable_bits

    # -----------------------------------------------------
    # FORMAT BER CURVES
    # -----------------------------------------------------

    curves = {}

    for name, result in comparison.items():
        curves[name] = {
            "snr": result["ebn0_db"].tolist(),
            "ber": [
                float(value) if value > 0 else None
                for value in result["ber"]
            ],
            "errors": result["errors"].tolist(),
        }

    # -----------------------------------------------------
    # CONSTELLATION DATA
    # -----------------------------------------------------

    # Limit response size while preserving useful visual detail.
    sample_count = min(2500, len(tx_symbols))

    constellation = {
        "tx_i": tx_symbols[:sample_count].real.tolist(),
        "tx_q": tx_symbols[:sample_count].imag.tolist(),
        "rx_i": rx_symbols[:sample_count].real.tolist(),
        "rx_q": rx_symbols[:sample_count].imag.tolist(),
    }

    # -----------------------------------------------------
    # TRANSMITTED AND RECEIVED BIT DATA
    # -----------------------------------------------------

    bit_data = {
        "tx": bits[:100].astype(int).tolist(),
        "rx": rx_bits[:100].astype(int).tolist(),
    }

    # -----------------------------------------------------
    # RETURN RESULTS TO ELECTRON
    # -----------------------------------------------------

    return {
        "ok": True,
        "schemes": schemes,
        "selected_scheme": scheme,
        "snr": snr,
        "num_bits": usable_bits,
        "errors": errors,
        "ber": measured_ber,
        "curves": curves,
        "constellation": constellation,
        "bits": bit_data,
    }


# ---------------------------------------------------------
# COMMAND-LINE ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    try:
        request_line = sys.stdin.readline()

        if not request_line.strip():
            raise ValueError("No simulation request was received.")

        request = json.loads(request_line)
        result = run_request(request)

        print(json.dumps(result, allow_nan=False))

    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "error": str(exc),
        }))
