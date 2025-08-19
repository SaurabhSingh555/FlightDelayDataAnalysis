import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Set up the page
st.set_page_config(
    page_title="Flight Data Analytics Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    st.markdown("""
    <style>
    .main-header {font-size: 2.5rem; color: #1f77b4; font-weight: 700;}
    .section-header {font-size: 1.8rem; color: #1f77b4; border-bottom: 2px solid #1f77b4; padding-bottom: 0.3rem;}
    .metric-label {font-size: 1rem; color: #7f7f7f;}
    .metric-value {font-size: 1.5rem; font-weight: 700;}
    .info-text {font-size: 0.9rem; color: #7f7f7f; font-style: italic;}
    </style>
    """, unsafe_allow_html=True)

load_css()

# Title and description
st.markdown('<p class="main-header">✈️ Flight Data Analytics Dashboard</p>', unsafe_allow_html=True)
st.markdown("""
This dashboard provides comprehensive analysis of flight operations, including performance metrics, delay patterns, 
and route analysis. Use the filters below to explore the data.
""")

# Load data
@st.cache_data
def load_data():
    # Load from CSV file
    df = pd.read_csv('cleaned_Merged_flight_data.csv')  # Replace with your actual file path
    
    # Convert date columns to datetime with the correct format
    date_cols = ['ScheduledDeparture', 'ActualDeparture', 'ScheduledArrival', 'ActualArrival']
    
    for col in date_cols:
        # Try different date formats
        try:
            df[col] = pd.to_datetime(df[col], format='%d-%m-%Y %H:%M')
        except:
            try:
                df[col] = pd.to_datetime(df[col], format='%m-%d-%Y %H:%M')
            except:
                df[col] = pd.to_datetime(df[col])  # Let pandas infer format
    
    return df

df = load_data()

# Sidebar filters
st.sidebar.header('Filters')

# Get unique airlines, handling any potential NaN values
airlines = df['Airline'].dropna().unique()
selected_airlines = st.sidebar.multiselect(
    'Select Airlines',
    options=airlines,
    default=airlines
)

# Get date range safely
try:
    min_date = df['ScheduledDeparture'].min()
    max_date = df['ScheduledDeparture'].max()
    
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date()
        )
    else:
        st.sidebar.warning("Date data not available for filtering")
        date_range = (None, None)
except Exception as e:
    st.sidebar.warning(f"Date filtering unavailable: {str(e)}")
    date_range = (None, None)

# Filter data based on selections
filtered_df = df[df['Airline'].isin(selected_airlines)]

# Apply date filter if available
if date_range[0] is not None and date_range[1] is not None:
    try:
        filtered_df = filtered_df[
            (filtered_df['ScheduledDeparture'].dt.date >= date_range[0]) & 
            (filtered_df['ScheduledDeparture'].dt.date <= date_range[1])
        ]
    except:
        st.sidebar.warning("Could not filter by date range")

# Key metrics
st.markdown('<p class="section-header">Key Performance Indicators</p>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_flights = len(filtered_df)
    st.markdown('<p class="metric-label">Total Flights</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="metric-value">{total_flights}</p>', unsafe_allow_html=True)

with col2:
    cancelled_flights = filtered_df['Cancelled'].sum() if 'Cancelled' in filtered_df.columns else 0
    st.markdown('<p class="metric-label">Cancelled Flights</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="metric-value">{cancelled_flights}</p>', unsafe_allow_html=True)

with col3:
    if total_flights > 0 and 'DelayMinutes' in filtered_df.columns:
        on_time_flights = filtered_df[filtered_df['DelayMinutes'] <= 0].shape[0]
        on_time_percentage = (on_time_flights / total_flights * 100)
    else:
        on_time_percentage = 0
    st.markdown('<p class="metric-label">On-Time Performance</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="metric-value">{on_time_percentage:.1f}%</p>', unsafe_allow_html=True)

with col4:
    if total_flights > 0 and 'DelayMinutes' in filtered_df.columns:
        avg_delay = filtered_df['DelayMinutes'].mean()
    else:
        avg_delay = 0
    st.markdown('<p class="metric-label">Average Delay (min)</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="metric-value">{avg_delay:.1f}</p>', unsafe_allow_html=True)

# Visualization section
st.markdown('<p class="section-header">Flight Performance Analysis</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Delay reasons chart
    if 'DelayReason' in filtered_df.columns:
        delay_reasons = filtered_df['DelayReason'].value_counts()
        fig = px.pie(
            values=delay_reasons.values, 
            names=delay_reasons.index,
            title='Delay Reasons Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("DelayReason data not available")

with col2:
    # Airlines performance
    if 'DelayMinutes' in filtered_df.columns:
        airline_stats = filtered_df.groupby('Airline').agg({
            'DelayMinutes': 'mean',
            'Cancelled': 'sum',
            'FlightID': 'count'
        }).rename(columns={'FlightID': 'TotalFlights'}).reset_index()
        
        fig = px.bar(
            airline_stats, 
            x='Airline', 
            y='DelayMinutes',
            title='Average Delay by Airline (minutes)',
            color='Airline'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Delay data not available for airline comparison")

# Route analysis
st.markdown('<p class="section-header">Route Analysis</p>', unsafe_allow_html=True)

# Create route column for analysis
if 'Origin' in filtered_df.columns and 'Destination' in filtered_df.columns:
    filtered_df['Route'] = filtered_df['Origin'] + ' - ' + filtered_df['Destination']

    route_stats = filtered_df.groupby('Route').agg({
        'DelayMinutes': 'mean',
        'Cancelled': 'sum',
        'FlightID': 'count',
        'Distance': 'first'
    }).rename(columns={'FlightID': 'TotalFlights'}).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            route_stats.nlargest(5, 'TotalFlights'), 
            x='Route', 
            y='TotalFlights',
            title='Top 5 Busiest Routes',
            color='Route'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if 'Distance' in route_stats.columns and 'DelayMinutes' in route_stats.columns:
            fig = px.scatter(
                route_stats,
                x='Distance',
                y='DelayMinutes',
                size='TotalFlights',
                color='Route',
                title='Delay vs Distance by Route',
                hover_name='Route'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Distance or Delay data not available for scatter plot")
else:
    st.info("Origin/Destination data not available for route analysis")

# Aircraft analysis
st.markdown('<p class="section-header">Aircraft Performance</p>', unsafe_allow_html=True)

if 'AircraftType' in filtered_df.columns and 'DelayMinutes' in filtered_df.columns:
    aircraft_stats = filtered_df.groupby('AircraftType').agg({
        'DelayMinutes': 'mean',
        'Cancelled': 'sum',
        'FlightID': 'count'
    }).rename(columns={'FlightID': 'TotalFlights'}).reset_index()

    fig = px.bar(
        aircraft_stats, 
        x='AircraftType', 
        y=['DelayMinutes'],
        title='Performance by Aircraft Type',
        labels={'value': 'Average Delay (minutes)', 'variable': 'Metric'},
        barmode='group'
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("AircraftType or Delay data not available")

# Raw data view
st.markdown('<p class="section-header">Flight Data</p>', unsafe_allow_html=True)
st.dataframe(filtered_df, use_container_width=True)

# Download button for filtered data
csv = filtered_df.to_csv(index=False)
st.download_button(
    label="Download Filtered Data as CSV",
    data=csv,
    file_name="filtered_flight_data.csv",
    mime="text/csv"
)

# Footer
st.markdown("---")
st.markdown('<p class="info-text">Flight Data Analytics Dashboard • Created for Coforge Interview Opportunity</p>', unsafe_allow_html=True)