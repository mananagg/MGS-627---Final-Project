import requests
import json
import pandas as pd
from datetime import datetime
import dash
from dash import dcc
from dash import html
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. API Configuration
# Enter your BLS API key here
api_key = "5e717f9be9784fd28faa6fa425915492"

# Define the BLS API endpoint and headers
url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
headers = {'Content-type': 'application/json'}

# Define the Series IDs for the data we want to fetch
series_ids = [
    "LNS11000000",  # Civilian Labor Force (Seasonally Adjusted)
    "LNS12000000",  # Civilian Employment (Seasonally Adjusted)
    "LNS13000000",  # Civilian Unemployment (Seasonally Adjusted)
    "LNS14000000",  # Unemployment Rate (Seasonally Adjusted)
    "CES0000000001",  # Total Nonfarm Employment (Seasonally Adjusted)
    "LNS11300000",  # Labor Force Participation Rate (Seasonally Adjusted)
    "LNS12300000"   # Employment-Population Ratio (Seasonally Adjusted)
]

# Define the time period for the data request
start_year = "2015"
end_year = str(datetime.now().year)

# Create the payload for the API request
payload = {
    "seriesid": series_ids,
    "startyear": start_year,
    "endyear": end_year,
    "registrationkey": api_key,
    "catalog": True,
    "calculations": True
}


# 2. Data Fetching and Processing
def fetch_bls_data():
    """
    Fetches data from the BLS API and processes it into a pandas DataFrame.
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
        # Use a more robust way to get the series name, falling back to ID if needed
        series_name = series['catalog'].get('series_title', series_id)

        series_data = pd.DataFrame(series['data'])
        series_data['date'] = pd.to_datetime(series_data['year'] + series_data['period'].str.replace('M', '-'))
        series_data.set_index('date', inplace=True)
        series_data['value'] = pd.to_numeric(series_data['value'])

        df[series_id] = series_data['value']

    return df


# Fetch the data
bls_df = fetch_bls_data()

# Exit if data fetching failed
if bls_df is None:
    print("Could not retrieve data. Please check your API key and network connection.")
    exit()

# Rename columns for clarity in the dashboard
bls_df = bls_df.rename(columns={
    "LNS11000000": "Civilian Labor Force",
    "LNS12000000": "Civilian Employment",
    "LNS13000000": "Civilian Unemployment",
    "LNS14000000": "Unemployment Rate",
    "CES0000000001": "Total Nonfarm Employment",
    "LNS11300000": "Labor Force Participation Rate",
    "LNS12300000": "Employment-Population Ratio"
})

# 3. KPI Calculations
bls_df['Monthly Change in Nonfarm Employment'] = bls_df['Total Nonfarm Employment'].diff()

# Get the latest data point's date
# Corrected logic to ensure we get the latest date from the DataFrame
latest_date = bls_df.index.max().strftime('%B %Y')


# 4. Dash App Layout and Callbacks
app = dash.Dash(__name__)

app.layout = html.Div(children=[
    html.H1(
        children='U.S. Labor Market Dashboard',
        style={
            'textAlign': 'center',
            'font-family': 'Helvetica Neue, Helvetica, Arial, sans-serif'
        }
    ),
    html.H3(
        f"All data is for the latest month: {latest_date}",
        style={
            'textAlign': 'center',
            'font-family': 'Helvetica Neue, Helvetica, Arial, sans-serif',
            'color': '#888'
        }
    ),

    # KPI Cards Section
    html.Div(
        children=[
            html.Div(
                children=[
                    html.H3("Unemployment Rate"),
                    html.P(f"{bls_df['Unemployment Rate'].iloc[-1]:.1f}%", style={'font-size': '2em'})
                ],
                style={'width': '18%', 'display': 'inline-block', 'margin': '1%', 'padding': '1%', 'border': '2px solid #ccc', 'border-radius': '10px'}
            ),
            html.Div(
                children=[
                    html.H3("Nonfarm Jobs Added"),
                    html.P(f"{bls_df['Monthly Change in Nonfarm Employment'].iloc[-1]:,.0f}", style={'font-size': '2em'})
                ],
                style={'width': '18%', 'display': 'inline-block', 'margin': '1%', 'padding': '1%', 'border': '2px solid #ccc', 'border-radius': '10px'}
            ),
            html.Div(
                children=[
                    html.H3("Total Nonfarm Employment"),
                    html.P(f"{bls_df['Total Nonfarm Employment'].iloc[-1]:,.0f}", style={'font-size': '2em'})
                ],
                style={'width': '18%', 'display': 'inline-block', 'margin': '1%', 'padding': '1%', 'border': '2px solid #ccc', 'border-radius': '10px'}
            ),
            html.Div(
                children=[
                    html.H3("Labor Force Participation Rate"),
                    html.P(f"{bls_df['Labor Force Participation Rate'].iloc[-1]:.1f}%", style={'font-size': '2em'})
                ],
                style={'width': '18%', 'display': 'inline-block', 'margin': '1%', 'padding': '1%', 'border': '2px solid #ccc', 'border-radius': '10px'}
            ),
            html.Div(
                children=[
                    html.H3("Employment-Population Ratio"),
                    html.P(f"{bls_df['Employment-Population Ratio'].iloc[-1]:.1f}%", style={'font-size': '2em'})
                ],
                style={'width': '18%', 'display': 'inline-block', 'margin': '1%', 'padding': '1%', 'border': '2px solid #ccc', 'border-radius': '10px'}
            ),
        ],
        style={'textAlign': 'center'}
    ),

    # Plots Section
    dcc.Graph(
        id='unemployment-rate-graph',
        figure=go.Figure(
            data=go.Scatter(
                x=bls_df.index,
                y=bls_df['Unemployment Rate'],
                mode='lines+markers',
                name='Unemployment Rate (%)',
                line=dict(color='firebrick', width=2)
            ),
            layout=go.Layout(
                title='U.S. Unemployment Rate',
                xaxis={'title': 'Date'},
                yaxis={'title': 'Unemployment Rate (%)'},
                template='plotly_dark'
            )
        )
    ),

    dcc.Graph(
        id='nonfarm-employment-graph',
        figure=go.Figure(
            data=go.Bar(
                x=bls_df.index,
                y=bls_df['Monthly Change in Nonfarm Employment'],
                name='Jobs Added/Lost (Monthly)'
            ),
            layout=go.Layout(
                title='Monthly Change in U.S. Nonfarm Employment',
                xaxis={'title': 'Date'},
                yaxis={'title': 'Change in Employment (in thousands)'},
                template='plotly_dark'
            )
        )
    ),

    dcc.Graph(
        id='labor-participation-graph',
        figure=go.Figure(
            data=go.Scatter(
                x=bls_df.index,
                y=bls_df['Labor Force Participation Rate'],
                mode='lines',
                name='Labor Force Participation Rate (%)',
                line=dict(color='skyblue', width=2)
            ),
            layout=go.Layout(
                title='Labor Force Participation Rate',
                xaxis={'title': 'Date'},
                yaxis={'title': 'Rate (%)'},
                template='plotly_dark'
            )
        )
    ),

    dcc.Graph(
        id='employment-population-graph',
        figure=go.Figure(
            data=go.Scatter(
                x=bls_df.index,
                y=bls_df['Employment-Population Ratio'],
                mode='lines',
                name='Employment-Population Ratio (%)',
                line=dict(color='lightgreen', width=2)
            ),
            layout=go.Layout(
                title='Employment-Population Ratio',
                xaxis={'title': 'Date'},
                yaxis={'title': 'Ratio (%)'},
                template='plotly_dark'
            )
        )
    ),

    dcc.Graph(
        id='employment-unemployment-graph',
        figure=make_subplots(
            specs=[[{"secondary_y": True}]],
            shared_xaxes=True
        )
    ),
])

@app.callback(
    dash.Output('employment-unemployment-graph', 'figure'),
    [dash.Input('unemployment-rate-graph', 'relayout')]
)
def update_employment_unemployment_graph(relayout_data):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=bls_df.index, y=bls_df['Civilian Employment'], name='Civilian Employment', line=dict(color='blue')), secondary_y=False)
    fig.add_trace(go.Scatter(x=bls_df.index, y=bls_df['Civilian Unemployment'], name='Civilian Unemployment', line=dict(color='orange')), secondary_y=True)
    fig.update_layout(title_text="U.S. Employment and Unemployment", template='plotly_dark')
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Civilian Employment (in thousands)", secondary_y=False)
    fig.update_yaxes(title_text="Civilian Unemployment (in thousands)", secondary_y=True)
    return fig


if __name__ == '__main__':
    app.run(debug=True)
