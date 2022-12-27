import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.queries import Subgraph
from utils.market_makers import StableSwapBinary, StableSwap
from utils.streamlit import Streamlit
from utils.html_components import Components

st.set_page_config(
   page_title="Simulation | Amp Factor",
   page_icon="📊",
   initial_sidebar_state="expanded",
   layout="wide",
)

if "pool_id" not in st.session_state:
  st.session_state["pool_data"] = {
    "pool_id": "0x06df3b2bbb68adc8b0e302443692037ed9f91b42000000000000000000000063",
    "network": "Ethereum"
  }

networks = ["Ethereum", "Polygon", "Arbitrum"]
network = st.sidebar.selectbox('Network', options=networks, index=0)
pool_id = st.sidebar.text_input('Pool id', value=st.session_state["pool_data"]["pool_id"])

subgraph = Subgraph(network)
response = subgraph.query_pool_by_id(pool_id)
if response["pool"] is None:
  Components.error_container('Pool not found error', f'The pool {pool_id} do not exist in the {network} network')

elif response["pool"]["poolType"] != "Stable":
  Components.error_container('Not stable pool error', f'The {response["pool"]["name"]} pool is not stable')

else:
  #initializing
  st_utils = Streamlit()
  st_utils.initiate_session_state("pool_data", response["pool"])
  st_utils.initiate_session_state("tokens", response["pool"]["tokens"])
  st_utils.initiate_session_state("names", [t["name"] for t in response["pool"]["tokens"]])
  st_utils.initiate_session_state("balances",[float(t["balance"]) for t in response["pool"]["tokens"]])
  st_utils.initiate_session_state("pool", {"pool_id": pool_id, "network": network})

  st.title(f'{st.session_state["pool_data"]["name"]} Simulation')
  col1, col2 = st.columns(2)
  
  base_amp = float(st.session_state["pool_data"]["amp"])
  amp_series = base_amp*np.append(np.logspace(-3, 0, endpoint=False), np.logspace(0, 3))
  new_amp = st.sidebar.select_slider('Amp factor', options=amp_series, value=base_amp)
  
  type_token_sell = st.sidebar.selectbox(label="Which token you want to sell?", options=st.session_state["names"])
  token_to_sell_index = st.session_state["names"].index(type_token_sell)
  other_tokens_index = [i for i in range(len(st.session_state["names"])) if i != token_to_sell_index]
  current_stable_swape = StableSwap(names=st.session_state["names"], amp=base_amp, balances=st.session_state["balances"])
  new_stable_swape = StableSwap(names=st.session_state["names"], amp=new_amp, balances=st.session_state["balances"])
  input_token_index = st.session_state["names"].index(type_token_sell)
  st_utils.initiate_session_state("x_data", st.session_state["pool_data"]["tokens"][token_to_sell_index])
  st_utils.initiate_session_state("y_data", [st.session_state["pool_data"]["tokens"][i] for i in other_tokens_index])
  x_data_name = st.session_state["x_data"]["name"]

  #sidebar
  balance = px.pie(values=st.session_state["balances"], names=st.session_state["names"], labels=st.session_state["names"], height=350)
  balance.update_traces(hovertemplate='<b>%{value}</b>')
  balance.update_layout(legend=dict(
    yanchor="top",
    y=0.01,
    xanchor="left",
    x=0.01
  ),title="Tokens distribution")
  st.sidebar.plotly_chart(balance, use_container_width=True)
  st.sidebar.write('Base Amp Factor :', base_amp)
  amount_token_sell = st.sidebar.number_input(label='How much of token {} you want to sell?'.format(type_token_sell),value=float(st.session_state["x_data"]["balance"])/10, step=0.1,max_value=float(st.session_state["x_data"]["balance"]), min_value=0.0)

  #depth cost
  col1.header("Depth Cost")
  depth_fig = st_utils.depth_cost_chart(current_stable_swape, new_stable_swape, base_amp, new_amp, st.session_state["x_data"],type_token_sell)
  st.plotly_chart(depth_fig, use_container_width=True)

  #price and pool
  tabs = st.tabs([y_data["name"] for y_data in st.session_state["y_data"]])
  for index in range(len(st.session_state["y_data"])):
    with tabs[index]:
      tab_col1, tab_col2 = tabs[index].columns(2)
      y_data = st.session_state["y_data"][index]
      base_y = float(y_data["balance"])
      df = pd.DataFrame()
      df[x_data_name] = np.linspace(float(current_stable_swape.constant)*0.2, float(current_stable_swape.constant)*0.8, num=100)
      
      df["Current curve"] = df[x_data_name].apply(lambda x: current_stable_swape.calculate_y(type_token_sell, y_data["name"], x)) 
      df["New curve"] = df[x_data_name].apply(lambda x: new_stable_swape.calculate_y(type_token_sell, y_data["name"], x))

      df["Current spot price"] = df[x_data_name].apply(lambda x: current_stable_swape.calculate_spot_price(type_token_sell, y_data["name"], x))
      df["New spot price"] = df[x_data_name].apply(lambda x: new_stable_swape.calculate_spot_price(type_token_sell, y_data["name"], x))

      new_transaction = new_stable_swape.calculate_trade(type_token_sell, y_data["name"], amount_token_sell)
      current_transaction = current_stable_swape.calculate_trade(type_token_sell, y_data["name"], amount_token_sell)
      
      #Spot price and price impact kpi
      st_utils.price_impact_kpi(tab_col1, tab_col2, current_stable_swape, current_transaction, new_stable_swape, new_transaction, y_data, base_amp, new_amp, type_token_sell)
      
      price_chart = st_utils.spot_price_chart(df, current_transaction, new_transaction, x_data_name)
      pool_chart = st_utils.pool_chart(df,current_transaction,new_transaction,x_data_name,y_data)
      
      st.plotly_chart(price_chart, use_container_width=True)
      st.plotly_chart(pool_chart, use_container_width=True)
