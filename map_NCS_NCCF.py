import geopandas as gpd
import pandas as pd

from dash import Dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

import plotly.express as px
import plotly.graph_objects as go

# ==========================================================
# SETTINGS
# ==========================================================

SHAPEFILE = "PPA-Final-2025.shp"
EXCEL_FILE = "B.xlsx"

REGION_COLUMN_SHP = "Region"
REGION_COLUMN_XLSX = "Reg"

EST_COLUMN = "No_of_Est"

# ==========================================================
# READ SHAPEFILE
# ==========================================================

print("Loading shapefile...")

gdf = gpd.read_file(SHAPEFILE)

# Fix geometry

gdf = (
    gdf
    .to_crs(4326)
)

gdf["geometry"] = gdf["geometry"].buffer(0)

# Aggregate to region

gdf = (
    gdf
    .dissolve(by=REGION_COLUMN_SHP)
    .reset_index()
)

# ==========================================================
# READ EXCEL
# ==========================================================

print("Loading Excel data...")

df = pd.read_excel(EXCEL_FILE)

# ==========================================================
# MERGE
# ==========================================================

gdf = gdf.merge(
    df,
    left_on=REGION_COLUMN_SHP,
    right_on=REGION_COLUMN_XLSX,
    how="left"
)

# Ranking

gdf = (
    gdf
    .sort_values(EST_COLUMN, ascending=False)
    .reset_index(drop=True)
)

gdf["Rank"] = gdf.index + 1

# ==========================================================
# CREATE INITIAL MAP
# ==========================================================

def create_map(selected_region=None):

    fig = px.choropleth_map(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color=EST_COLUMN,
        hover_name=REGION_COLUMN_SHP,
        hover_data={
            EST_COLUMN: ":,.0f",
            "Rank": True
        },
        center={
            "lat": 12.8797,
            "lon": 121.7740
        },
        zoom=4.8,
        opacity=0.85
    )

    fig.update_geos(fitbounds="locations")

    fig.update_layout(
        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0
        )
    )

    if selected_region is not None:

        selected = gdf[
            gdf[REGION_COLUMN_SHP] == selected_region
        ]

        if len(selected) > 0:

            centroid = selected.geometry.iloc[0].centroid

            fig.update_layout(
                mapbox_center=dict(
                    lat=centroid.y,
                    lon=centroid.x
                ),
                mapbox_zoom=7
            )

    return fig

# ==========================================================
# DASH APP
# ==========================================================

app = Dash(__name__)

app.layout = html.Div([

    html.H1(
        "Number of Establishments by Region",
        style={
            "textAlign": "center"
        }
    ),

    html.Div([

        html.Button(
            "Back to Philippines",
            id="reset-btn",
            n_clicks=0,
            style={
                "marginBottom":"10px"
            }
        ),

        dcc.Graph(
            id="map",
            figure=create_map(),
            style={
                "height":"80vh"
            }
        )

    ], style={
        "width":"60%",
        "display":"inline-block",
        "verticalAlign":"top"
    }),

    html.Div([

        html.H2("Region Profile"),

        html.Div(
            id="region-profile"
        ),

        dcc.Graph(
            id="ranking-chart"
        )

    ], style={
        "width":"38%",
        "display":"inline-block",
        "padding":"20px",
        "verticalAlign":"top"
    })

])

# ==========================================================
# CALLBACK
# ==========================================================

@app.callback(
    [
        Output("map","figure"),
        Output("region-profile","children"),
        Output("ranking-chart","figure")
    ],
    [
        Input("map","clickData"),
        Input("reset-btn","n_clicks")
    ]
)
def update_dashboard(clickData, reset_clicks):

    from dash import callback_context

    ctx = callback_context

    trigger = ctx.triggered[0]["prop_id"]

    if "reset-btn" in trigger:

        region_text = html.Div([
            html.H3("Philippines"),
            html.P("Click a region to view details.")
        ])

        bar = px.bar(
            gdf.sort_values(
                EST_COLUMN,
                ascending=True
            ),
            x=EST_COLUMN,
            y=REGION_COLUMN_SHP,
            orientation="h",
            title="Regional Ranking"
        )

        return (
            create_map(),
            region_text,
            bar
        )

    if clickData is None:

        region_text = html.Div([
            html.H3("Philippines"),
            html.P("Click a region to view details.")
        ])

        bar = px.bar(
            gdf.sort_values(
                EST_COLUMN,
                ascending=True
            ),
            x=EST_COLUMN,
            y=REGION_COLUMN_SHP,
            orientation="h",
            title="Regional Ranking"
        )

        return (
            create_map(),
            region_text,
            bar
        )

    idx = clickData["points"][0]["location"]

    row = gdf.iloc[idx]

    region_name = row[REGION_COLUMN_SHP]

    profile = html.Div([

        html.H2(region_name),

        html.H3(
            f"{int(row[EST_COLUMN]):,}"
        ),

        html.P(
            "Establishments"
        ),

        html.H4(
            f"Rank #{int(row['Rank'])}"
        )

    ])

    ranking = px.bar(
        gdf.sort_values(
            EST_COLUMN,
            ascending=False
        ).head(10),
        x=REGION_COLUMN_SHP,
        y=EST_COLUMN,
        title=f"Top Regions"
    )

    return (
        create_map(region_name),
        profile,
        ranking
    )

# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=8050
    )