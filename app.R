library(shiny)
library(leaflet)
library(sf)
library(dplyr)
library(readxl)
library(scales)

# ============================================================
# CONFIGURATION & PORTABLE ENVIRONMENT
# ============================================================
sf_use_s2(FALSE)
BASE_DIR <- "." 

# ============================================================
# DATA INGESTION & PROCESSING
# ============================================================
ph_map <- st_read(file.path(BASE_DIR, "PPA-Final-2025.shp"), quiet = TRUE) %>%
  st_make_valid() %>%
  st_transform(4326)

est_data <- read_excel(file.path(BASE_DIR, "B.xlsx"))

ph_map <- left_join(ph_map, est_data, by = c("Region" = "Reg"))
ph_map$No_of_Est <- as.numeric(ph_map$No_of_Est)

ph_reg <- ph_map %>%
  group_by(Region) %>%
  summarise(No_of_Est = first(No_of_Est), .groups = "drop") %>%
  st_make_valid()

ph_bbox <- st_bbox(ph_reg)
xmin <- unname(ph_bbox["xmin"])
ymin <- unname(ph_bbox["ymin"])
xmax <- unname(ph_bbox["xmax"])
ymax <- unname(ph_bbox["ymax"])

pal <- colorNumeric(
  palette = "YlGnBu",
  domain = ph_reg$No_of_Est,
  na.color = "#eceff1"
)

# ============================================================
# UI DESIGN (MODERNIZED & EMBED-READY)
# ============================================================
ui <- fluidPage(
  title = "Philippines Establishment Map",
  
  tags$head(
    tags$style(HTML("
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
      
      body, html {
        font-family: 'Inter', sans-serif;
        background-color: #f4f6f8;
        margin: 0;
        padding: 0;
        height: 100vh;
        width: 100vw;
        overflow: hidden;
      }
      
      .main-container {
        display: flex;
        height: 100vh;
        width: 100vw;
      }
      
      .map-wrapper {
        flex: 1;
        position: relative;
        height: 100%;
      }
      
      #map {
        height: 100% !important;
        width: 100% !important;
      }
      
      .floating-controls {
        position: absolute;
        top: 16px;
        left: 16px;
        z-index: 1000;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(8px);
        padding: 8px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      }
      
      .btn-custom-home {
        background: #1e293b;
        color: white;
        border: none;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
        border-radius: 6px;
        transition: background 0.2s ease;
      }
      
      .btn-custom-home:hover {
        background: #0f172a;
        color: #38bdf8;
      }
      
      .sidebar-panel {
        width: 360px;
        background: #ffffff;
        box-shadow: -4px 0 24px rgba(0,0,0,0.06);
        display: flex;
        flex-direction: column;
        z-index: 1001;
        border-left: 1px solid #e2e8f0;
      }
      
      .sidebar-header {
        padding: 24px;
        background: #1e293b;
        color: white;
      }
      
      .sidebar-header h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: -0.5px;
      }
      
      .sidebar-header p {
        margin: 4px 0 0 0;
        font-size: 12px;
        color: #94a3b8;
      }
      
      .sidebar-content {
        padding: 24px;
        flex: 1;
        overflow-y: auto;
      }
      
      .info-card-empty {
        text-align: center;
        color: #64748b;
        margin-top: 40px;
      }
      
      .info-card-empty h3 {
        font-weight: 600; 
        color: #334155; 
        font-size: 15px;
        margin-bottom: 6px;
      }
      
      .stat-box {
        background: #f8fafc;
        border-left: 4px solid #0ea5e9;
        padding: 16px;
        border-radius: 0 8px 8px 0;
        margin-top: 16px;
      }
      
      .stat-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748b;
        font-weight: 600;
      }
      
      .stat-value {
        font-size: 30px;
        font-weight: 700;
        color: #0f172a;
        margin-top: 4px;
      }
      
      .btn-close-panel {
        width: 100%;
        background: #f1f5f9;
        color: #475569;
        border: none;
        padding: 12px;
        border-radius: 6px;
        font-weight: 600;
        margin-top: 24px;
        transition: background 0.2s, color 0.2s;
      }
      
      .btn-close-panel:hover {
        background: #e2e8f0;
        color: #0f172a;
      }
    "))
  ),
  
  div(class = "main-container",
      div(class = "map-wrapper",
          div(class = "floating-controls",
              actionButton("home", "🏠 Reset Map View", class = "btn-custom-home")
          ),
          leafletOutput("map")
      ),
      div(class = "sidebar-panel",
          div(class = "sidebar-header",
              h2("Regional Analytics"),
              p("National Census Dashboard")
          ),
          div(class = "sidebar-content",
              uiOutput("region_info")
          )
      )
  )
)

# ============================================================
# SERVER LOGIC
# ============================================================
server <- function(input, output, session) {
  selected_region <- reactiveVal(NULL)
  
  output$map <- renderLeaflet({
    leaflet(ph_reg) %>%
      addProviderTiles(providers$CartoDB.PositronNoLabels) %>%
      addProviderTiles(providers$CartoDB.PositronOnlyLabels) %>%
      addPolygons(
        layerId = ~Region,
        fillColor = ~pal(No_of_Est),
        fillOpacity = 0.75,
        color = "#ffffff",
        weight = 1,
        label = ~Region,
        highlightOptions = highlightOptions(
          weight = 3,
          color = "#0ea5e9",
          fillOpacity = 0.85,
          bringToFront = TRUE
        )
      ) %>%
      fitBounds(lng1 = xmin, lat1 = ymin, lng2 = xmax, lat2 = ymax)
  })
  
  observeEvent(input$map_shape_click, {
    click <- input$map_shape_click
    req(click$id)
    
    selected_region(click$id)
    selected <- ph_reg %>% filter(Region == click$id)
    bb <- st_bbox(selected)
    
    leafletProxy("map") %>%
      clearGroup("flash_layer") %>% 
      addPolygons(
        data = selected,
        fillColor = "#38bdf8", 
        fillOpacity = 0.4,
        color = "#0ea5e9",
        weight = 3,
        group = "flash_layer"
      ) %>%
      fitBounds(
        lng1 = unname(bb["xmin"]), lat1 = unname(bb["ymin"]),
        lng2 = unname(bb["xmax"]), lat2 = unname(bb["ymax"])
      )
  })
  
  output$region_info <- renderUI({
    if (is.null(selected_region())) {
      return(
        div(class = "info-card-empty",
            h3("No Region Selected"),
            p("Interact with the map boundaries to view structural data.")
        )
      )
    }
    
    info <- ph_reg %>% filter(Region == selected_region())
    
    div(
      h3(style = "font-weight: 700; color: #0f172a; margin-top: 0;", info$Region),
      div(class = "stat-box",
          div(class = "stat-label", "Total Establishments"),
          div(class = "stat-value", comma(info$No_of_Est))
      ),
      actionButton("close_panel", "Clear Selection", class = "btn-close-panel")
    )
  })
  
  observeEvent(input$close_panel, {
    selected_region(NULL)
    leafletProxy("map") %>% clearGroup("flash_layer")
  })
  
  observeEvent(input$home, {
    selected_region(NULL)
    leafletProxy("map") %>%
      clearGroup("flash_layer") %>%
      fitBounds(lng1 = xmin, lat1 = ymin, lng2 = xmax, lat2 = ymax)
  })
}

shinyApp(ui, server)
