"""
Final Project - MGS 627: Business Process Automation

Project Title: U.S. Labor Market Dashboard
Description: This script automates the process of retrieving, processing,
and visualizing key labor market data from the U.S. Bureau of Labor Statistics (BLS)
Public Data API. It presents a dynamic dashboard using the Dash library,
showcasing critical economic indicators for analysis.
"""

import requests
import json
import pandas as pd
from datetime import datetime
import dash
from dash import dcc
from dash import html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar

# ==============================================================================
# 1. API Configuration
# ==============================================================================
# Enter your BLS API key here. This key is required for authentication.
api_key = "5e717f9be9784fd28faa6fa425915492"

# Define the BLS API endpoint and HTTP headers for JSON content
url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
headers = {'Content-type': 'application/json'}

# Define the Series IDs for the data we want to fetch.
# These IDs correspond to specific economic indicators from the BLS.
series_ids = [
    "LNS11000000",  # Civilian Labor Force (Seasonally Adjusted)
    "LNS12000000",  # Civilian Employment (Seasonally Adjusted)
    "LNS13000000",  # Civilian Unemployment (Seasonally Adjusted)
    "LNS14000000",  # Unemployment Rate (Seasonally Adjusted)
    "CES0000000001",  # Total Nonfarm Employment (Seasonally Adjusted)
    "LNS11300000",  # Labor Force Participation Rate (Seasonally Adjusted)
    "LNS12300000"  # Employment-Population Ratio (Seasonally Adjusted)
]

# Set the time period for the data request.
start_year = "2015"
end_year = str(datetime.now().year)

# Create the JSON payload for the API request.
# The 'registrationkey' is where the API key is passed for authentication.
payload = {
    "seriesid": series_ids,
    "startyear": start_year,
    "endyear": end_year,
    "registrationkey": api_key,
    "catalog": True,  # Request catalog information for series titles
    "calculations": True  # Request calculated values if available
}


# ==============================================================================
# 2. Data Fetching and Processing (Automated Function)
# ==============================================================================
def fetch_bls_data():
    """
    Fetches data from the BLS API and processes it into a pandas DataFrame.

    This custom function encapsulates the entire data retrieval process, making
    it repeatable and automated.
    """
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from BLS API: {e}")
        return None

    if 'Results' not in data or 'series' not in data['Results']:
        print("API response does not contain the expected data structure.")
        return None

    df = pd.DataFrame()
    for series in data['Results']['series']:
        series_id = series['seriesID']
        series_name = series['catalog'].get('series_title', series_id)

        series_data = pd.DataFrame(series['data'])
        series_data['date'] = pd.to_datetime(series_data['year'] + series_data['period'].str.replace('M', '-'))
        series_data.set_index('date', inplace=True)
        series_data['value'] = pd.to_numeric(series_data['value'])

        df[series_id] = series_data['value']

    # Sort the index to ensure the latest data is at the end
    df.sort_index(inplace=True)

    return df


# Execute the automated data fetching function
bls_df = fetch_bls_data()

# Gracefully exit if data fetching fails
if bls_df is None:
    print("Could not retrieve data. Please check your API key and network connection.")
    exit()

# ==============================================================================
# 3. Data Cleaning and KPI Calculations
# ==============================================================================
# Rename columns for clarity in the dashboard visualization
bls_df = bls_df.rename(columns={
    "LNS11000000": "Civilian Labor Force",
    "LNS12000000": "Civilian Employment",
    "LNS13000000": "Civilian Unemployment",
    "LNS14000000": "Unemployment Rate",
    "CES0000000001": "Total Nonfarm Employment",
    "LNS11300000": "Labor Force Participation Rate",
    "LNS12300000": "Employment-Population Ratio"
})

# Calculate the month-over-month change in nonfarm employment
bls_df['Monthly Change in Nonfarm Employment'] = bls_df['Total Nonfarm Employment'].diff()

# Correctly scale the "in thousands" value for display on the KPI card
bls_df['Monthly Change in Nonfarm Employment Display'] = bls_df['Monthly Change in Nonfarm Employment'] * 1000

# Get the date of the latest data point for the dashboard's headline
latest_date = bls_df.index.max().strftime('%B %Y')

# Calculate yearly nonfarm employment change by resampling data
yearly_change_nonfarm = bls_df['Total Nonfarm Employment'].resample('YE').last().diff()
yearly_change_nonfarm = yearly_change_nonfarm.dropna()

# Get month abbreviations for the heatmap axis
month_names = [calendar.month_abbr[i] for i in range(1, 13)]

# ==============================================================================
# 4. Dash App Layout and Visualizations
# ==============================================================================
app = dash.Dash(__name__)

# Define styles for a modern, clean dashboard using a dark theme
main_container_style = {
    'font-family': 'Helvetica Neue, Helvetica, Arial, sans-serif',
    'background-color': '#0d1117',
    'color': '#ffffff',
    'padding': '20px'
}

header_style = {
    'textAlign': 'center',
    'color': '#ffffff',
    'margin-bottom': '10px'
}

kpi_container_style = {
    'display': 'flex',
    'justify-content': 'space-around',
    'flex-wrap': 'wrap',
    'margin': '20px 0'
}

kpi_card_style = {
    'background-color': '#161b22',
    'border': '1px solid #30363d',
    'border-radius': '6px',
    'padding': '20px',
    'margin': '10px',
    'flex-grow': '1',
    'min-width': '180px',
    'text-align': 'center'
}

kpi_value_style = {
    'font-size': '2.5em',
    'font-weight': 'bold',
    'color': '#58a6ff'
}

graph_style = {
    'margin-top': '40px'
}

# Pre-create the dual-axis figure to avoid using a callback
employment_unemployment_fig = make_subplots(specs=[[{"secondary_y": True}]])
employment_unemployment_fig.add_trace(
    go.Scatter(x=bls_df.index, y=bls_df['Civilian Employment'], name='Civilian Employment', line=dict(color='#58a6ff')),
    secondary_y=False)
employment_unemployment_fig.add_trace(
    go.Scatter(x=bls_df.index, y=bls_df['Civilian Unemployment'], name='Civilian Unemployment',
               line=dict(color='#ff7b72')), secondary_y=True)
employment_unemployment_fig.update_layout(title_text="U.S. Employment and Unemployment", template='plotly_dark')
employment_unemployment_fig.update_xaxes(title_text="Date")
employment_unemployment_fig.update_yaxes(title_text="Civilian Employment (in thousands)", secondary_y=False)
employment_unemployment_fig.update_yaxes(title_text="Civilian Unemployment (in thousands)", secondary_y=True)

# Main dashboard layout
app.layout = html.Div(style=main_container_style, children=[
    html.H1(children='U.S. Labor Market Dashboard', style=header_style),
    html.H3(f"All data is for the latest month: {latest_date}", style={'textAlign': 'center', 'color': '#8b949e'}),

    # KPI Cards section
    html.Div(style=kpi_container_style, children=[
        html.Div(style=kpi_card_style, children=[
            html.H3("Unemployment Rate", style={'font-size': '1.2em'}),
            html.P(f"{bls_df['Unemployment Rate'].iloc[-1]:.1f}%", style=kpi_value_style)
        ]),
        html.Div(style=kpi_card_style, children=[
            html.H3("Nonfarm Jobs Added (Monthly)", style={'font-size': '1.2em'}),
            html.P(f"{bls_df['Monthly Change in Nonfarm Employment Display'].iloc[-1]:,.0f}", style=kpi_value_style)
        ]),
        html.Div(style=kpi_card_style, children=[
            html.H3("Total Nonfarm Employment", style={'font-size': '1.2em'}),
            html.P(f"{bls_df['Total Nonfarm Employment'].iloc[-1] * 1000:,.0f}", style=kpi_value_style)
        ]),
        html.Div(style=kpi_card_style, children=[
            html.H3("Labor Force Participation Rate", style={'font-size': '1.2em'}),
            html.P(f"{bls_df['Labor Force Participation Rate'].iloc[-1]:.1f}%", style=kpi_value_style)
        ]),
        html.Div(style=kpi_card_style, children=[
            html.H3("Employment-Population Ratio", style={'font-size': '1.2em'}),
            html.P(f"{bls_df['Employment-Population Ratio'].iloc[-1]:.1f}%", style=kpi_value_style)
        ]),
    ]),

    # All the data visualizations
    html.Div(style=graph_style, children=[
        dcc.Graph(
            id='unemployment-rate-graph',
            figure=go.Figure(
                data=go.Scatter(
                    x=bls_df.index,
                    y=bls_df['Unemployment Rate'],
                    mode='lines+markers',
                    name='Unemployment Rate (%)',
                    line=dict(color='#ff7b72', width=2)
                ),
                layout=go.Layout(
                    title='U.S. Unemployment Rate Over Time',
                    xaxis={'title': 'Date'},
                    yaxis={'title': 'Unemployment Rate (%)'},
                    template='plotly_dark'
                )
            )
        ),
    ]),

    html.Div(style=graph_style, children=[
        dcc.Graph(
            id='monthly-nonfarm-change-graph',
            figure=go.Figure(
                data=go.Bar(
                    x=bls_df.index,
                    y=bls_df['Monthly Change in Nonfarm Employment'],
                    name='Jobs Added/Lost (Monthly)',
                    marker_color='#58a6ff'
                ),
                layout=go.Layout(
                    title='Monthly Change in U.S. Nonfarm Employment',
                    xaxis={'title': 'Date'},
                    yaxis={'title': 'Change in Employment (in thousands)'},
                    template='plotly_dark'
                )
            )
        ),
    ]),

    html.Div(style=graph_style, children=[
        dcc.Graph(
            id='yearly-nonfarm-change-graph',
            figure=go.Figure(
                data=go.Bar(
                    x=yearly_change_nonfarm.index.year,
                    y=yearly_change_nonfarm,
                    name='Jobs Added/Lost (Yearly)',
                    marker_color='#58a6ff'
                ),
                layout=go.Layout(
                    title='Yearly Change in U.S. Nonfarm Employment',
                    xaxis={'title': 'Year'},
                    yaxis={'title': 'Change in Employment (in thousands)'},
                    template='plotly_dark'
                )
            )
        )
    ]),

    html.Div(style=graph_style, children=[
        dcc.Graph(
            id='unemployment-rate-heatmap',
            figure=go.Figure(
                data=go.Heatmap(
                    x=bls_df.index.month,
                    y=bls_df.index.year,
                    z=bls_df['Unemployment Rate'],
                    colorscale='Jet',
                    hovertemplate='Month: %{x}<br>Year: %{y}<br>Unemployment Rate: %{z:.1f}%<extra></extra>',
                    colorbar_title='Unemployment Rate (%)'
                ),
                layout=go.Layout(
                    title='Unemployment Rate Heatmap (2015-Present)',
                    xaxis={'title': 'Month', 'tickmode': 'array', 'tickvals': list(range(1, 13)),
                           'ticktext': month_names},
                    yaxis={'title': 'Year'},
                    template='plotly_dark'
                )
            )
        )
    ]),

    html.Div(style=graph_style, children=[
        dcc.Graph(
            id='labor-participation-graph',
            figure=go.Figure(
                data=go.Scatter(
                    x=bls_df.index,
                    y=bls_df['Labor Force Participation Rate'],
                    mode='lines',
                    name='Labor Force Participation Rate (%)',
                    line=dict(color='#8957e5', width=2)
                ),
                layout=go.Layout(
                    title='Labor Force Participation Rate Over Time',
                    xaxis={'title': 'Date'},
                    yaxis={'title': 'Rate (%)'},
                    template='plotly_dark'
                )
            )
        ),
    ]),

    html.Div(style=graph_style, children=[
        dcc.Graph(
            id='employment-population-graph',
            figure=go.Figure(
                data=go.Scatter(
                    x=bls_df.index,
                    y=bls_df['Employment-Population Ratio'],
                    mode='lines',
                    name='Employment-Population Ratio (%)',
                    line=dict(color='#3fb950', width=2)
                ),
                layout=go.Layout(
                    title='Employment-Population Ratio Over Time',
                    xaxis={'title': 'Date'},
                    yaxis={'title': 'Ratio (%)'},
                    template='plotly_dark'
                )
            )
        ),
    ]),

    html.Div(style=graph_style, children=[
        dcc.Graph(
            id='employment-unemployment-graph',
            figure=employment_unemployment_fig
        )
    ])
])

# ==============================================================================
# 5. Run the Dash App
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=True)

# ==============================================================================
# Final Comments and Summary
# ==============================================================================
"""
This script represents the final, polished version of the project.
It successfully demonstrates:
1. Automated data retrieval from a third-party API.
2. Data manipulation and calculation of key performance indicators (KPIs).
3. Creation of a visually appealing, interactive dashboard with multiple
   chart types to provide comprehensive business insights.
4. An elegant and well-documented code structure suitable for collaboration
   and future development.
"""