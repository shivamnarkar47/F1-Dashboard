import streamlit as st
import fastf1 as ff1
import fastf1.plotting
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configure FastF1 cache
# ff1.Cache.enable_cache('f1_cache')

# Set page configuration
st.set_page_config(
    page_title="F1 Analytics Dashboard",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #FF1801;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #1E1E1E;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #FF1801;
    }
</style>
""", unsafe_allow_html=True)

class F1Dashboard:
    def __init__(self):
        self.years = list(range(2018, datetime.now().year + 1))
        self.years.reverse()
        
    def load_session_data(self, year, gp, session):
        """Load session data from FastF1"""
        try:
            session = ff1.get_session(year, gp, session)
            session.load()
            return session
        except Exception as e:
            st.error(f"Error loading session data: {e}")
            return None
    
    def get_available_events(self, year):
        """Get available events for selected year"""
        try:
            schedule = ff1.get_event_schedule(year)
            return schedule
        except:
            return pd.DataFrame()

def main():
    st.markdown('<h1 class="main-header">🏎️ F1 Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    dashboard = F1Dashboard()
    
    # Sidebar for controls
    with st.sidebar:
        st.header("Session Configuration")
        
        selected_year = st.selectbox("Season", dashboard.years, index=0)
        
        # Get events for selected year
        schedule = dashboard.get_available_events(selected_year)
        if not schedule.empty:
            event_names = schedule['EventName'].tolist()
            selected_event = st.selectbox("Grand Prix", event_names)
        else:
            selected_event = st.text_input("Grand Prix", "Monaco")
        
        session_type = st.selectbox(
            "Session Type",
            ['Race', 'Qualifying', 'Practice 1', 'Practice 2', 'Practice 3', 'Sprint', 'Sprint Qualifying']
        )
        
        st.header("Visualization Options")
        show_lap_times = st.checkbox("Show Lap Times", True)
        show_telemetry = st.checkbox("Show Telemetry", True)
        show_position_changes = st.checkbox("Show Position Changes", True)
        show_tire_strategy = st.checkbox("Show Tire Strategy", True)
        
        if st.button("Load Session Data"):
            st.session_state.load_data = True
        else:
            st.session_state.load_data = False

    # Main dashboard
    if st.session_state.get('load_data', False):
        with st.spinner(f"Loading {session_type} data for {selected_event} {selected_year}..."):
            session = dashboard.load_session_data(selected_year, selected_event, session_type)
            
            if session is not None:
                display_session_data(session, selected_year, selected_event, session_type,
                                   show_lap_times, show_telemetry, show_position_changes, show_tire_strategy)
            else:
                st.error("Failed to load session data. Please check your inputs and try again.")

    else:
        show_welcome_screen()

def display_session_data(session, year, event, session_type, show_lap_times, show_telemetry, show_position_changes, show_tire_strategy):
    """Display all session data and visualizations"""
    
    # Session overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Season", year)
    with col2:
        st.metric("Event", event)
    with col3:
        st.metric("Session", session_type)
    with col4:
        if hasattr(session, 'laps') and not session.laps.empty:
            st.metric("Total Laps", len(session.laps['LapNumber'].unique()))
    
    st.markdown("---")
    
    # Results table
    if hasattr(session, 'results') and not session.results.empty:
        st.subheader("Session Results")
        results_display = session.results[['Position', 'Abbreviation', 'TeamName', 'Points']]
        st.dataframe(results_display, use_container_width=True)
    
    # Visualizations in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Lap Analysis", "Telemetry", "Race Progress", "Tire Strategy"])
    
    with tab1:
        if show_lap_times:
            display_lap_times(session)
    
    with tab2:
        if show_telemetry:
            display_telemetry_comparison(session)
    
    with tab3:
        if show_position_changes:
            display_position_changes(session)
    
    with tab4:
        if show_tire_strategy:
            display_tire_strategy(session)

def display_lap_times(session):
    """Display lap time analysis"""
    st.subheader("Lap Time Analysis")
    
    if not hasattr(session, 'laps') or session.laps.empty:
        st.warning("No lap data available for this session.")
        return
    
    laps = session.laps
    drivers = session.drivers
    
    # Driver selection
    col1, col2 = st.columns(2)
    with col1:
        selected_drivers = st.multiselect(
            "Select Drivers",
            options=drivers,
            default=drivers[:3] if len(drivers) >= 3 else drivers
        )
    
    if not selected_drivers:
        st.warning("Please select at least one driver.")
        return
    
    # Prepare lap time data
    fig = go.Figure()
    
    for driver in selected_drivers:
        driver_laps = laps.pick_driver(driver)
        if not driver_laps.empty:
            fig.add_trace(go.Scatter(
                x=driver_laps['LapNumber'],
                y=driver_laps['LapTime'].dt.total_seconds(),
                mode='lines+markers',
                name=f"{session.get_driver(driver)['Abbreviation']}",
                line=dict(width=2)
            ))
    
    fig.update_layout(
        title="Lap Times Comparison",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        height=500,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Fastest laps comparison
    st.subheader("Fastest Laps Comparison")
    
    fastest_laps = []
    for driver in selected_drivers:
        driver_fastest = laps.pick_driver(driver).pick_fastest()
        if not driver_fastest.empty:
            fastest_laps.append({
                'Driver': session.get_driver(driver)['Abbreviation'],
                'LapTime': driver_fastest['LapTime'].total_seconds(),
                'LapNumber': driver_fastest['LapNumber'],
                'Compound': driver_fastest['Compound']
            })
    
    if fastest_laps:
        fastest_df = pd.DataFrame(fastest_laps)
        fastest_df = fastest_df.sort_values('LapTime')
        
        fig_bar = px.bar(
            fastest_df,
            x='Driver',
            y='LapTime',
            color='Compound',
            title="Fastest Lap Times by Driver",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

def display_telemetry_comparison(session):
    """Display telemetry comparison between drivers"""
    st.subheader("Telemetry Comparison")
    
    if not hasattr(session, 'laps') or session.laps.empty:
        st.warning("No telemetry data available for this session.")
        return
    
    laps = session.laps
    drivers = session.drivers
    
    if len(drivers) < 2:
        st.warning("Need at least 2 drivers for telemetry comparison.")
        return
    
    # Driver selection for telemetry
    col1, col2 = st.columns(2)
    with col1:
        driver1 = st.selectbox("Driver 1", drivers, index=0, key="driver1")
    with col2:
        driver2 = st.selectbox("Driver 2", drivers, index=min(1, len(drivers)-1), key="driver2")
    
    # Get fastest laps
    try:
        lap_driver1 = laps.pick_driver(driver1).pick_fastest()
        lap_driver2 = laps.pick_driver(driver2).pick_fastest()
        
        tel_driver1 = lap_driver1.get_telemetry()
        tel_driver2 = lap_driver2.get_telemetry()
        
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Speed (km/h)', 'Throttle (%)', 'Brake'),
            vertical_spacing=0.1
        )
        
        # Speed
        fig.add_trace(
            go.Scatter(x=tel_driver1['Distance'], y=tel_driver1['Speed'],
                      name=f"{session.get_driver(driver1)['Abbreviation']} Speed",
                      line=dict(color='red')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=tel_driver2['Distance'], y=tel_driver2['Speed'],
                      name=f"{session.get_driver(driver2)['Abbreviation']} Speed",
                      line=dict(color='blue')),
            row=1, col=1
        )
        
        # Throttle
        fig.add_trace(
            go.Scatter(x=tel_driver1['Distance'], y=tel_driver1['Throttle'],
                      name=f"{session.get_driver(driver1)['Abbreviation']} Throttle",
                      line=dict(color='red'), showlegend=False),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=tel_driver2['Distance'], y=tel_driver2['Throttle'],
                      name=f"{session.get_driver(driver2)['Abbreviation']} Throttle",
                      line=dict(color='blue'), showlegend=False),
            row=2, col=1
        )
        
        # Brake
        fig.add_trace(
            go.Scatter(x=tel_driver1['Distance'], y=tel_driver1['Brake'],
                      name=f"{session.get_driver(driver1)['Abbreviation']} Brake",
                      line=dict(color='red'), showlegend=False),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=tel_driver2['Distance'], y=tel_driver2['Brake'],
                      name=f"{session.get_driver(driver2)['Abbreviation']} Brake",
                      line=dict(color='blue'), showlegend=False),
            row=3, col=1
        )
        
        fig.update_layout(height=800, title_text="Telemetry Comparison")
        fig.update_xaxes(title_text="Distance (m)", row=3, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading telemetry data: {e}")

def display_position_changes(session):
    """Display position changes during the race using Plotly"""
    st.subheader("Position Changes")
    
    if not hasattr(session, 'laps') or session.laps.empty:
        st.warning("No position data available for this session.")
        return
    
    try:
        # Setup FastF1 for driver colors
        fastf1.plotting.setup_mpl(mpl_timedelta_support=False, color_scheme='fastf1')
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Plot each driver's position
        for drv in session.drivers:
            drv_laps = session.laps.pick_driver(drv)
            
            if len(drv_laps) == 0:
                continue
                
            # Get driver abbreviation and style
            abb = drv_laps['Driver'].iloc[0] if 'Driver' in drv_laps.columns else str(drv)
            
            # Get driver color from FastF1
            try:
                driver_color = fastf1.plotting.get_driver_color(abb, session)
                driver_name = session.get_driver(drv)['Abbreviation']
            except:
                driver_color = '#808080'  # Default gray if color not found
                driver_name = abb
            
            # Create hover text with additional info
            hover_text = []
            for _, lap in drv_laps.iterrows():
                compound = lap.get('Compound', 'N/A')
                stint = lap.get('Stint', 'N/A')
                hover_text.append(
                    f"Driver: {driver_name}<br>"
                    f"Lap: {lap['LapNumber']}<br>"
                    f"Position: {lap['Position']}<br>"
                    f"Compound: {compound}<br>"
                    f"Stint: {stint}"
                )
            
            # Add driver trace to plot
            fig.add_trace(go.Scatter(
                x=drv_laps['LapNumber'],
                y=drv_laps['Position'],
                mode='lines',
                name=driver_name,
                line=dict(color=driver_color, width=2),
                hoverinfo='text',
                hovertext=hover_text,
                showlegend=True
            ))
        
        # Update layout to match matplotlib style
        fig.update_layout(
            title="Position Changes During Race",
            xaxis_title="Lap",
            yaxis_title="Position",
            height=500,
            showlegend=True,
            hovermode='closest',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Configure y-axis to match matplotlib settings
        fig.update_yaxes(
            autorange="reversed",  # Position 1 at top, like in matplotlib
            range=[20.5, 0.5],     # Set limits
            tickvals=[1, 5, 10, 15, 20],  # Specific tick positions
            dtick=1,               # Show all integer positions
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        )
        
        # Configure x-axis
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        )
        
        # Display the plot
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Could not generate position changes plot: {e}")

def display_tire_strategy(session):
    """Display tire strategy information"""
    st.subheader("Tire Strategy")
    
    if not hasattr(session, 'laps') or session.laps.empty:
        st.warning("No tire data available for this session.")
        return
    
    laps = session.laps
    drivers = session.drivers
    
    # Tire stint analysis
    stints_data = []
    for driver in drivers:
        driver_laps = laps.pick_driver(driver)
        if not driver_laps.empty:
            stints = driver_laps[['LapNumber', 'Compound', 'Stint']]
            stints = stints.groupby('Stint').agg({
                'LapNumber': ['min', 'max', 'count'],
                'Compound': 'first'
            }).reset_index()
            
            stints.columns = ['Stint', 'StartLap', 'EndLap', 'LapCount', 'Compound']
            
            for _, stint in stints.iterrows():
                stints_data.append({
                    'Driver': session.get_driver(driver)['Abbreviation'],
                    'Stint': stint['Stint'],
                    'StartLap': stint['StartLap'],
                    'EndLap': stint['EndLap'],
                    'LapCount': stint['LapCount'],
                    'Compound': stint['Compound']
                })
    
    if stints_data:
        stints_df = pd.DataFrame(stints_data)
        
        # Create tire strategy plot
        fig = go.Figure()
        
        for compound in stints_df['Compound'].unique():
            compound_data = stints_df[stints_df['Compound'] == compound]
            fig.add_trace(go.Scatter(
                x=compound_data['StartLap'],
                y=compound_data['Driver'],
                mode='markers',
                marker=dict(
                    size=15,
                    symbol='square'
                ),
                name=compound,
                hovertemplate='Driver: %{y}<br>Start Lap: %{x}<br>Compound: ' + compound
            ))
        
        fig.update_layout(
            title="Tire Strategy",
            xaxis_title="Lap Number",
            yaxis_title="Driver",
            height=500,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Stint summary table
        st.subheader("Stint Summary")
        st.dataframe(stints_df, use_container_width=True)

def show_welcome_screen():
    """Display welcome screen with instructions"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## Welcome to the F1 Analytics Dashboard! 🏎️
        
        This dashboard provides comprehensive analysis of Formula 1 race data including:
        
        - **Lap Time Analysis**: Compare lap times between drivers
        - **Telemetry Data**: Speed, throttle, and brake comparison
        - **Position Changes**: Track how positions changed during the race
        - **Tire Strategies**: Analyze tire compound usage and stint lengths
        
        ### How to use:
        1. Select the season, grand prix, and session type from the sidebar
        2. Choose which visualizations to display
        3. Click 'Load Session Data' to generate the dashboard
        
        ### Supported Sessions:
        - Race
        - Qualifying
        - Practice Sessions
        - Sprint Races
        
        *Note: Data availability depends on the session and year selected.*
        """)
    
    with col2:
        st.image("https://logos-download.com/wp-content/uploads/2019/11/Formula_1_Logo.png", 
                width=300, caption="Formula 1")
        
        st.info("""
        **Pro Tip**: 
        The first time loading data for a session may take longer as it downloads from the FastF1 API. Subsequent loads will be faster due to caching.
        """)

if __name__ == "__main__":
    main()