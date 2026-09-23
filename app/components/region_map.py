"""
AURA Mars — Region Map Component

Renders a static Mars surface map with markers for candidate regions.
Uses a base image with Plotly scatter overlay for markers.
"""

from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from src.comparison import load_region_metadata


def render_region_map():
    """
    Render a static Mars map with markers for each candidate region.

    Uses a Plotly scatter plot positioned over a Mars map image.
    If no map image is available, falls back to a simple scatter plot.
    """
    try:
        data = load_region_metadata()
    except Exception as e:
        st.warning(f"Could not load region data: {e}")
        return

    regions = data["regions"]

    # Extract coordinates and labels
    names = [r["name"] for r in regions]
    lats = [r["lat"] for r in regions]
    lons = [r["lon"] for r in regions]
    descriptions = [r["description"] for r in regions]

    # Check for map image
    map_image_path = Path(__file__).parent.parent / "assets" / "mars_map.png"

    fig = go.Figure()

    if map_image_path.exists():
        # Overlay markers on the Mars map image
        from PIL import Image
        img = Image.open(map_image_path)
        fig.add_layout_image(
            dict(
                source=img,
                xref="x", yref="y",
                x=-180, y=90,
                sizex=360, sizey=180,
                sizing="stretch",
                layer="below",
            )
        )

    # Add region markers
    fig.add_trace(go.Scatter(
        x=lons,
        y=lats,
        mode="markers+text",
        marker=dict(size=14, color="#e74c3c", symbol="diamond"),
        text=names,
        textposition="top center",
        textfont=dict(size=12, color="white"),
        hovertext=descriptions,
        hoverinfo="text",
        name="Candidate Regions",
    ))

    fig.update_layout(
        title="Candidate Mars Regions",
        xaxis=dict(title="Longitude (°E)", range=[-180, 180]),
        yaxis=dict(title="Latitude (°N)", range=[-90, 90]),
        height=400,
        margin=dict(t=50, b=30, l=30, r=30),
        plot_bgcolor="#1a1a2e",
        paper_bgcolor="#16213e",
        font=dict(color="white"),
    )

    st.plotly_chart(fig, width="stretch", key="region_map_chart")
