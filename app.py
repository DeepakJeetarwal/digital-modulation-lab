
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.modulation import SUPPORTED_SCHEMES, modulate, demodulate
from src.channel import add_awgn
from src.simulation import run_comparison


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Digital Modulation Lab",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Warm, premium colour palette
BG = "#F7F5F0"
CARD = "#FFFFFF"
TEXT = "#30372F"
MUTED = "#77796F"
BORDER = "#E7E2D9"
SAGE = "#71866B"
SAGE_LIGHT = "#E8EEE4"
COPPER = "#B98159"
BLUE = "#7895A5"
PURPLE = "#A18CB7"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {{
        color-scheme: light;
    }}

    html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif;
        color: {TEXT};
    }}

    .stApp {{
        background: {BG};
    }}

    [data-testid="stHeader"] {{
        background: rgba(247,245,240,0.92);
    }}

    [data-testid="stSidebar"] {{
        background: #F0EDE5;
        border-right: 1px solid {BORDER};
    }}

    [data-testid="stSidebar"] > div:first-child {{
        padding-top: 1.5rem;
    }}

    h1, h2, h3 {{
        font-family: 'Manrope', sans-serif !important;
        color: {TEXT} !important;
        letter-spacing: -0.5px;
    }}

    h1 {{
        font-weight: 800 !important;
    }}

    p, label, .stMarkdown {{
        color: {TEXT};
    }}

    [data-testid="stMetric"] {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 19px 20px;
        box-shadow: 0 3px 12px rgba(50,45,35,0.035);
    }}

    [data-testid="stMetricLabel"] p {{
        color: {MUTED} !important;
        font-size: 0.82rem !important;
    }}

    [data-testid="stMetricValue"] {{
        color: {TEXT} !important;
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 20px;
    }}

    div.stButton > button {{
        border-radius: 10px;
        border: 1px solid {BORDER};
        background: {CARD};
        color: {TEXT};
        font-weight: 600;
        transition: all 0.2s ease;
    }}

    div.stButton > button:hover {{
        border-color: {SAGE};
        color: {SAGE};
        background: {SAGE_LIGHT};
    }}

    div.stButton > button[kind="primary"] {{
        background: {SAGE};
        color: white;
        border: 1px solid {SAGE};
    }}

    div.stButton > button[kind="primary"]:hover {{
        background: #5D7258;
        color: white;
    }}

    [data-testid="stSlider"] [role="slider"] {{
        background: {SAGE};
    }}

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {{
        border: 1px solid {BORDER};
        border-radius: 10px;
        overflow: hidden;
    }}

    .hero {{
        padding: 8px 0 20px 0;
    }}

    .eyebrow {{
        color: {SAGE};
        text-transform: uppercase;
        font-size: 0.73rem;
        font-weight: 700;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }}

    .subtitle {{
        color: {MUTED};
        font-size: 1rem;
        margin-top: -8px;
    }}

    .section-label {{
        color: {MUTED};
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.4px;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 18px;
        border-bottom: 1px solid {BORDER};
    }}

    .stTabs [data-baseweb="tab"] {{
        color: {MUTED};
        font-weight: 600;
    }}

    .stTabs [aria-selected="true"] {{
        color: {SAGE} !important;
    }}

    hr {{
        border-color: {BORDER};
    }}

    footer {{
        visibility: hidden;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown(
    f"""
    <div class="hero">
        <div class="eyebrow">COMMUNICATION SYSTEMS · LAB 01</div>
        <h1 style="font-size:2.45rem; margin-bottom:10px;">
            Digital Modulation Lab
        </h1>
        <div class="subtitle">
            Effect of SNR Variation on Different Digital Modulation Schemes
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:
    st.markdown("## Experiment setup")
    st.caption("Configure your transmission experiment.")

    selected_schemes = st.multiselect(
        "Modulation schemes",
        options=list(SUPPORTED_SCHEMES),
        default=list(SUPPORTED_SCHEMES),
    )

    ebn0_db = st.slider(
        "Energy per bit / noise ratio (dB)",
        min_value=0,
        max_value=20,
        value=8,
        step=1,
    )

    num_bits = st.selectbox(
        "Number of transmitted bits",
        options=[12000, 30000, 60000, 120000],
        index=1,
        format_func=lambda x: f"{x:,} bits",
    )

    seed = st.number_input(
        "Random seed",
        min_value=0,
        max_value=999999,
        value=42,
        step=1,
    )

    st.markdown("---")
    st.markdown("**Quick SNR presets**")

    preset_cols = st.columns(4)

    for col, value in zip(preset_cols, [0, 5, 10, 20]):
        if col.button(f"{value} dB", key=f"preset_{value}"):
            st.session_state["snr"] = value

    st.markdown("---")

    run_clicked = st.button(
        "Run simulation  →",
        type="primary",
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("**ABOUT THIS EXPERIMENT**")
    st.caption(
        "AWGN channel · Coherent detection · "
        "BER performance · Four modulation schemes"
    )


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "snr" not in st.session_state:
    st.session_state["snr"] = 8

if "results" not in st.session_state:
    st.session_state["results"] = None

if "constellation" not in st.session_state:
    st.session_state["constellation"] = None

# If a preset was selected, synchronize the slider on rerun.
# Keep the current value unless the user used a preset.
if st.session_state["snr"] != ebn0_db:
    ebn0_db = st.session_state["snr"]


# ---------------------------------------------------------
# SIMULATION
# ---------------------------------------------------------

if run_clicked:
    if not selected_schemes:
        st.warning("Select at least one modulation scheme.")
    else:
        snr_values = np.arange(0, 21, 2)

        with st.spinner("Running transmission experiment..."):
            results = run_comparison(
                schemes=selected_schemes,
                ebn0_db_values=snr_values,
                num_bits=int(num_bits),
                seed=int(seed),
            )

            scheme = selected_schemes[0]
            k = {
                "BPSK": 1,
                "QPSK": 2,
                "8-PSK": 3,
                "16-QAM": 4,
            }[scheme]

            rng = np.random.default_rng(int(seed))
            usable_bits = (int(num_bits) // k) * k

            bits = rng.integers(
                0, 2, size=usable_bits, dtype=np.uint8
            )

            tx_symbols = modulate(bits, scheme)
            rx_symbols = add_awgn(
                tx_symbols,
                float(ebn0_db),
                scheme,
                rng=rng,
            )

            rx_bits = demodulate(rx_symbols, scheme)

            st.session_state["results"] = results
            st.session_state["constellation"] = {
                "scheme": scheme,
                "tx_symbols": tx_symbols[:3000],
                "rx_symbols": rx_symbols[:3000],
                "tx_bits": bits[:100],
                "rx_bits": rx_bits[:100],
                "errors": int(np.count_nonzero(bits != rx_bits)),
                "total_bits": usable_bits,
                "snr": ebn0_db,
            }


results = st.session_state["results"]
constellation = st.session_state["constellation"]


# ---------------------------------------------------------
# CHART THEME
# ---------------------------------------------------------

def style_chart(fig, height=430):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(
            family="DM Sans, sans-serif",
            color=TEXT,
            size=12,
        ),
        margin=dict(l=20, r=20, t=35, b=20),
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=BORDER,
            borderwidth=1,
        ),
        xaxis=dict(
            gridcolor="#EEEAE2",
            zerolinecolor=BORDER,
            linecolor=BORDER,
        ),
        yaxis=dict(
            gridcolor="#EEEAE2",
            zerolinecolor=BORDER,
            linecolor=BORDER,
        ),
    )
    return fig


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

if results is None:
    st.info(
        "Configure the experiment on the left, then select "
        "'Run simulation' to view your results."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Modulation schemes", "4")

    with c2:
        st.metric("Channel model", "AWGN")

    with c3:
        st.metric("Main performance metric", "BER")

    st.markdown("### Experiment overview")

    st.write(
        "This laboratory studies how energy per bit relative to "
        "noise power spectral density affects the reliability of "
        "digital communication systems."
    )

else:
    # -----------------------------------------------------
    # TOP METRICS
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-label">EXPERIMENT OVERVIEW</div>',
        unsafe_allow_html=True,
    )

    selected_scheme = constellation["scheme"]

    result = results[selected_scheme]
    index = int(
        np.argmin(np.abs(result["ebn0_db"] - ebn0_db))
    )

    measured_ber = result["ber"][index]
    measured_errors = result["errors"][index]

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Eb/N0", f"{ebn0_db} dB")
    m2.metric("Selected modulation", selected_scheme)
    m3.metric("Measured BER", f"{measured_ber:.5g}")
    m4.metric("Bit errors", f"{measured_errors:,}")

    st.markdown("")

    # -----------------------------------------------------
    # TABS
    # -----------------------------------------------------

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "BER performance",
            "Constellation",
            "Bit transmission",
            "Numerical results",
        ]
    )

    with tab1:
        st.markdown("### BER vs. Eb/N0")
        st.caption(
            "Compare the measured bit error rate over the AWGN channel."
        )

        colors = {
            "BPSK": SAGE,
            "QPSK": BLUE,
            "8-PSK": COPPER,
            "16-QAM": PURPLE,
        }

        fig = go.Figure()

        for scheme, data in results.items():
            ber = [
                float(v) if v > 0 else None
                for v in data["ber"]
            ]

            fig.add_trace(
                go.Scatter(
                    x=data["ebn0_db"],
                    y=ber,
                    mode="lines+markers",
                    name=scheme,
                    connectgaps=False,
                    line=dict(color=colors[scheme], width=2.8),
                    marker=dict(size=7),
                    hovertemplate=(
                        "Eb/N0: %{x} dB<br>"
                        "BER: %{y:.6g}<extra>%{fullData.name}</extra>"
                    ),
                )
            )

        fig.update_layout(
            title="Measured bit error rate",
            xaxis_title="Eb/N0 (dB)",
            yaxis_title="Bit error rate (BER)",
            yaxis_type="log",
        )

        style_chart(fig, 480)
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Zero measured errors are omitted on the logarithmic axis; "
            "they do not indicate a theoretical BER of zero."
        )

    with tab2:
        st.markdown(
            f"### Received constellation · {constellation['scheme']}"
        )
        st.caption(
            f"AWGN channel at Eb/N0 = {ebn0_db} dB. "
            "Change the SNR and run the experiment again to compare."
        )

        rx = constellation["rx_symbols"]
        tx = constellation["tx_symbols"]

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=rx.real,
                y=rx.imag,
                mode="markers",
                name="Received symbols",
                marker=dict(
                    size=5,
                    color=SAGE,
                    opacity=0.42,
                ),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=tx.real,
                y=tx.imag,
                mode="markers",
                name="Ideal constellation",
                marker=dict(
                    size=11,
                    color=COPPER,
                    symbol="x",
                ),
            )
        )

        fig.update_layout(
            title="In-phase vs. quadrature",
            xaxis_title="In-phase (I)",
            yaxis_title="Quadrature (Q)",
            yaxis=dict(scaleanchor="x", scaleratio=1),
        )

        style_chart(fig, 560)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("### Transmitted vs. received bits")
        st.caption("The first 100 bits from the constellation experiment.")

        tx_bits = constellation["tx_bits"].astype(int)
        rx_bits = constellation["rx_bits"].astype(int)

        comparison = pd.DataFrame({
            "Position": np.arange(1, len(tx_bits) + 1),
            "Transmitted": tx_bits,
            "Received": rx_bits,
            "Status": np.where(tx_bits == rx_bits, "Correct", "Error"),
        })

        st.dataframe(
            comparison,
            use_container_width=True,
            hide_index=True,
        )

        visible_errors = int(np.count_nonzero(tx_bits != rx_bits))

        st.metric(
            "Errors in the displayed 100 bits",
            visible_errors,
        )

        st.caption(
            "This count covers only the displayed 100 bits, "
            "not the entire simulation."
        )

    with tab4:
        st.markdown("### Numerical results")

        rows = []

        for scheme, data in results.items():
            for snr, errors, ber in zip(
                data["ebn0_db"],
                data["errors"],
                data["ber"],
            ):
                rows.append({
                    "Modulation": scheme,
                    "Eb/N0 (dB)": float(snr),
                    "Bit errors": int(errors),
                    "Total bits": int(data["total_bits"]),
                    "BER": float(ber),
                })

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download results as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="snr_modulation_results.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.markdown("---")

left, right = st.columns([3, 1])

with left:
    st.caption(
        "DIGITAL COMMUNICATIONS LAB · AWGN CHANNEL · BER ANALYSIS"
    )

with right:
    st.caption("Python · Streamlit · Plotly")
