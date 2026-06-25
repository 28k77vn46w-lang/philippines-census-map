import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
import json

# ============================================================
# PAGE CONFIGURATION (MODERN FULL-WIDTH LAYOUT)
# ============================================================
st.set_page_config(
    page_title="Philippines Establishment Map",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom fonts and layout styling to match your original R UI design
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #f4f6f8;
    }
    .stat-box {
        background: #f8fafc;
        border-left: 4px solid #0ea5e9;
        padding: 16px;
        border-radius: 0 8px 8px 0;
        margin-top: 16px;
    }
    .stat-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
        font-weight: 600;
    }
    .stat-value {
        font-size: 32px;
        font-weight: 700;
        color: #0f172a;
        margin-top: 4px;
    }
    .sidebar-header-custom {
        padding: 24px;
        background: #1e293b;
        color: white;
        border-radius: 8px 8px 0 0;
        margin-bottom: 20px;
    }
    .sidebar-header-custom h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 700;
        color: #ffffff !important;
        letter-spacing: -0.5px;
    }
    .sidebar-header-custom p {
        margin: 4px 0 0 0;
        font-size: 12px;
        color: #94a3b8;
    }
    .info-card-empty {
        text-align: center;
        color: #64748b;
        margin-top: 40px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize reactive state trackers for clicking interactions
if "selected_region" not in st.session_state:
    st.session_state.selected_region = None

# ============================================================
# DATA CACHING & PROCESSING PIPELINE
# ============================================================
@st.cache_data
def load_and_clean_data():
    # 1. Read shapefile and completely patch spatial geometry defects
    ph_map = gpd.read_file("PPA-Final-2025.shp")
    ph_map["geometry"] = ph_map["geometry"].make_valid()
    ph_map = ph_map.to_crs(epsg=4326)
    
    # 2. Ingest master registry spreadsheet
    est_data = pd.read_excel("B.xlsx")
    
    # 3. Merge data frames
    merged = ph_map.merge(est_data, left_on="Region", right_on="Reg", how="left")
    merged["No_of_Est"] = pd.to_numeric(merged["No_of_Est"]).fillna(0)
    
    # 4. Collapse boundaries by Region
    ph_reg = merged.dissolve(by="Region", aggfunc={"No_of_Est": "first"}).reset_index()
    ph_reg["geometry"] = ph_reg["geometry"].make_valid()
    
    return ph_reg

try:
    ph_reg = load_and_clean_data()
except Exception as e:
    st.error(f"Error initializing architectural files: {e}")
    st.stop()

# Compute country default layout tracking bounds
country_bounds = ph_reg.total_bounds  # [xmin, ymin, xmax, ymax]

# Dynamic Bounds Determination based on selection state
if st.session_state.selected_region is not None:
    selected_geo = ph_reg[ph_reg["Region"] == st.session_state.selected_region]
    if not selected_geo.empty:
        # Extract the specific bounding box of the clicked region
        current_bounds = selected_geo.total_bounds
    else:
        current_bounds = country_bounds
else:
    current_bounds = country_bounds

center_lat = (current_bounds[1] + current_bounds[3]) / 2
center_lon = (current_bounds[0] + current_bounds[2]) / 2

# ============================================================
# DASHBOARD MASTER INTERFACE
# ============================================================
col_map, col_info = st.columns([0.65, 0.35])

with col_map:
    # Reset layout macro
    if st.button("🏠 Reset Map View"):
        st.session_state.selected_region = None
        st.rerun()
        
    # Generate interactive background folium matrix
    m = folium.Map(
        location=[center_lat, center_lon], 
        tiles="CartoDB positron",
        zoom_control=True
    )
    
    # Adjust zoom boundaries dynamically to focus selection window frame
    m.fit_bounds([[current_bounds[1], current_bounds[0]], [current_bounds[3], current_bounds[2]]])
    
    # Apply YlGnBu color palette scale rules
    choropleth = folium.Choropleth(
        geo_data=ph_reg.to_json(),
        data=ph_reg,
        columns=["Region", "No_of_Est"],
        key_on="feature.properties.Region",
        fill_color="YlGnBu",
        fill_opacity=0.75,
        line_color="white",
        line_weight=1,
        highlight=True,
        legend_name="Total Regional Establishments"
    ).add_to(m)
    
    # Inject active hover data tooltips
    folium.GeoJsonTooltip(
        fields=["Region", "No_of_Est"],
        aliases=["Region:", "Establishments:"],
        localize=True,
        sticky=False,
        labels=True,
        style="""
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            border-radius: 4px;
            padding: 6px;
        """
    ).add_to(choropleth.geojson)
    
    # Output map element to window frame and listen for clicks
    map_data = st_folium(m, width="100%", height=650, key="ph_map_framework")
    
    # Capture bounding adjustments when user selects a boundary poly
    if map_data and map_data.get("last_active_drawing"):
        clicked_props = map_data["last_active_drawing"].get("properties")
        if clicked_props and "Region" in clicked_props:
            new_selection = clicked_props["Region"]
            if st.session_state.selected_region != new_selection:
                st.session_state.selected_region = new_selection
                st.rerun()

with col_info:
    # Custom Header Styling
    st.markdown("""
        <div class="sidebar-header-custom">
            <h2>Regional Analytics</h2>
            <p>National Census Dashboard</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Render UI dependent on focus state
    if st.session_state.selected_region is None:
        st.markdown("""
            <div class="info-card-empty">
                <h3 style="font-weight:600; color:#334155; font-size:16px;">No Region Selected</h3>
                <p style="font-size:13px;">Interact with the map boundaries to view details.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Extract metadata matching user selection target
        region_name = st.session_state.selected_region
        selected_row = ph_reg[ph_reg["Region"] == region_name]
        
        if not selected_row.empty:
            total_est = int(selected_row.iloc[0]["No_of_Est"])
            formatted_value = f"{total_est:,}"
            
            st.markdown(f"### {region_name}")
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">Total Establishments</div>
                    <div class="stat-value">{formatted_value}</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("") # Whitespace structural cushion
            if st.button("Clear Selection", use_container_width=True):
                st.session_state.selected_region = None
                st.rerun()