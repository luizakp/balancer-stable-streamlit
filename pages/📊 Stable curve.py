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
  st_utils = Streamlit()
  html_components = Components()
  st_utils.initiate_session_state("pool_data", response["pool"])
  st_utils.initiate_session_state("tokens", response["pool"]["tokens"])
  st_utils.initiate_session_state("names", [t["name"] for t in response["pool"]["tokens"]])
  st_utils.initiate_session_state("balances",[float(t["balance"]) for t in response["pool"]["tokens"]])
  st_utils.initiate_session_state("pool", {"pool_id": pool_id, "network": network})
  base_amp = float(st.session_state["pool_data"]["amp"])
  amp_series = base_amp*np.append(np.logspace(-3, 0, endpoint=False), np.logspace(0, 3))
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
  new_amp = st.sidebar.select_slider('Amp factor', options=amp_series, value=base_amp)
  type_token_sell = st.sidebar.selectbox(label="Which token you want to sell?", options=st.session_state["names"])
  token_to_sell_index = st.session_state["names"].index(type_token_sell)
  other_tokens_index = [i for i in range(len(st.session_state["names"])) if i != token_to_sell_index]
  st_utils.initiate_session_state("x_data", st.session_state["pool_data"]["tokens"][token_to_sell_index])
  st_utils.initiate_session_state("y_data", [st.session_state["pool_data"]["tokens"][i] for i in other_tokens_index])
  amount_token_sell = st.sidebar.number_input(label='How much of token {} you want to sell?'.format(type_token_sell),value=float(st.session_state["x_data"]["balance"])/10, step=0.1,max_value=float(st.session_state["x_data"]["balance"]), min_value=0.0)

  st.title(f'{st.session_state["pool_data"]["name"]} Simulation')
  col1, col2 = st.columns(2)
  col1.header("Depth Cost")

  input_token_index = st.session_state["names"].index(type_token_sell)
  indexes_to_plot = [i for i in range(len(st.session_state["names"])) if i != input_token_index]
  current_stable_swape = StableSwap(names=st.session_state["names"], amp=base_amp, balances=st.session_state["balances"])
  new_stable_swape = StableSwap(names=st.session_state["names"], amp=new_amp, balances=st.session_state["balances"])
  base_x = float(st.session_state["x_data"]["balance"])
  x_data_name = st.session_state["x_data"]["name"]


  rows = []
  for pool, amp_tag, amp in zip([current_stable_swape, new_stable_swape], ["Current", "New"], [base_amp, new_amp]):
    for price_tag, price in zip(["-2%", "+2%"], [-0.02, 0.02]):
      for index in range(len(st.session_state["y_data"])):
        y_data = st.session_state["y_data"][index]
        row = dict()
        row["Pair token"] = y_data["name"]
        row["Amp factor"] = amp_tag
        row["Amp factor value"] = amp

        # considering 2 percentage of cost change
        row["Current price"] = float(pool.calculate_spot_price(x_data_name, y_data["name"], base_x))
        row["Price change"] = price_tag
        row["Price Target"] = row["Current price"]*(1+price)
        row["Cost"] = pool.calculate_value_to_spot_price(x_data_name, y_data["name"], row["Price Target"])
        rows.append(row)

  df = pd.DataFrame.from_records(rows)
  depth_fig = px.bar(df, x='Pair token', y="Cost", color="Amp factor", facet_col="Price change", barmode="group")
  title = "2% Depth Cost Analysis for {}".format(type_token_sell)
  depth_fig.update_layout(title=title, yaxis_title=type_token_sell)
  st.plotly_chart(depth_fig, use_container_width=True)

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

      fig = go.Figure(go.Scatter(
          name = "Default Amp Factor",
          x = df[x_data_name],
          y = df["Current curve"],
          hovertemplate =
          '<b>Price: %{text}</b>',
          text = df["Current spot price"].map('{:.5f}'.format)))

      fig.add_trace(go.Scatter(
          name = "New Amp Factor",
          x = df[x_data_name],
          y = df["New curve"],
          hovertemplate = '<b>Price: %{text}</b>',
          text = df["New spot price"].map('{:.5f}'.format)))

      fig.update_layout(hovermode='x unified')

      price = go.Figure(go.Scatter(
        name = "Default Amp Factor",
        x = df[x_data_name],
        y = df["Current spot price"],
        hovertemplate ='<b>Price: %{text}</b>',
        text = df["Current spot price"].map('{:.5f}'.format)
      ))

      price.add_trace(go.Scatter(
        name = "New Amp Factor",
        x = df[x_data_name],
        y = df["New spot price"],
        hovertemplate = '<b>Price: %{text}</b>',
        text = df["New spot price"].map('{:.5f}'.format)
      ))

      price.update_layout(hovermode='x unified')

      type_token_buy = y_data["name"]
      new_transaction = new_stable_swape.calculate_trade(type_token_sell, y_data["name"], amount_token_sell)
      current_transaction = current_stable_swape.calculate_trade(type_token_sell, y_data["name"], amount_token_sell)
      
      new_amount_token_buy = new_transaction['amount_token_buy']
      current_amount_token_buy = current_transaction['amount_token_buy']
      
      current_initial_spot_price = current_stable_swape.calculate_spot_price(st.session_state["x_data"]["name"], y_data["name"], current_transaction['transaction_sell'][0])
      current_final_spot_price = current_stable_swape.calculate_spot_price(st.session_state["x_data"]["name"], y_data["name"], current_transaction['transaction_sell'][1])
      current_price_impact = current_stable_swape.calculate_price_impact(current_initial_spot_price,current_final_spot_price)
      current_transaction['spot_price'] = [float(current_initial_spot_price),float(current_final_spot_price)]
      
      new_initial_spot_price = new_stable_swape.calculate_spot_price(st.session_state["x_data"]["name"], y_data["name"], new_transaction['transaction_sell'][0])
      new_final_spot_price = new_stable_swape.calculate_spot_price(st.session_state["x_data"]["name"], y_data["name"], new_transaction['transaction_sell'][1])
      new_price_impact = new_stable_swape.calculate_price_impact(new_initial_spot_price,new_final_spot_price)
      new_transaction['spot_price'] = [float(new_initial_spot_price),float(new_final_spot_price)]

      current_amp_dict = {'amp':base_amp, 'type_token_buy': y_data["name"], 'amount_token_buy':current_transaction['amount_token_buy'], 'price':current_transaction['price'], 'default_price':current_transaction['price'], 'price_impact':current_price_impact, 'default_price_impact':current_price_impact }
      new_amp_dict = {'amp':new_amp, 'type_token_buy': y_data["name"], 'amount_token_buy':new_transaction['amount_token_buy'], 'price':new_transaction['price'], 'default_price':current_transaction['price'], 'price_impact':new_price_impact,'default_price_impact':current_price_impact }
      
      price_delta = float(100-((new_transaction['price']/current_transaction['price'])*100))
      price_impact_delta = float(100-((new_price_impact/current_price_impact)*100))

      if new_amp != base_amp:
        tab_col1.subheader(f'Amp factor {new_amp:.5f}')
        tab_col1.write(f'Will receive {new_amount_token_buy:.5f} of {type_token_buy}')
        tab_col1.metric(label=f"Price of {type_token_buy} for 1 {type_token_sell}", value=float(new_transaction['price']), delta=f'{price_delta}%')
        tab_col1.metric(label="Price Impact", value=float(new_price_impact), delta=f'{price_impact_delta}%')

        tab_col2.subheader(f'Amp factor {base_amp:.5f}')
        tab_col2.write(f'Will receive {current_amount_token_buy:.5f} of {type_token_buy}')
        tab_col2.metric(label=f"Price of {type_token_buy} for 1 {type_token_sell}", value=float(current_transaction['price']))
        tab_col2.metric(label="Price Impact", value=float(current_price_impact))
      else:
        st.subheader(f'Amp factor {base_amp:.5f}')
        st.write(f'Will receive {current_amount_token_buy:.5f} of {type_token_buy}')
        st.metric(label=f"Price of {type_token_buy} for 1 {type_token_sell}", value=float(current_transaction['price']))
        st.metric(label="Price Impact", value=float(current_price_impact))

      fig.add_scatter(mode="markers",x=current_transaction['transaction_sell'],y=current_transaction['transaction_buy'], text=current_transaction['label'],name="", hovertemplate='%{text} <br> %{x}; %{y}',         
        marker=dict(
            color='#2533F8',
            size=7,
        ), showlegend=False)
      fig.add_scatter(mode="markers",x=new_transaction['transaction_sell'],y=new_transaction['transaction_buy'], text=new_transaction['label'],name="",hovertemplate='%{x}; %{y}',         
        marker=dict(
            color='#ED3C1D',
            size=7,
        ), showlegend=False)

      price.add_scatter(mode="markers",x=current_transaction['transaction_sell'],y=current_transaction['spot_price'], text=current_transaction['label'],name="", hovertemplate='%{text} <br> %{y}',         
        marker=dict(
            color='#2533F8',
            size=7,
        ), showlegend=False)

      price.add_scatter(mode="markers",x=new_transaction['transaction_sell'],y=new_transaction['spot_price'], text=new_transaction['label'],name="",hovertemplate='%{y}',         
        marker=dict(
            color='#ED3C1D',
            size=7,
        ), showlegend=False)

      fig.update_layout(xaxis_title=st.session_state["x_data"]["name"], yaxis_title=y_data["name"], title="Pool")
      price.update_layout(xaxis_title=st.session_state["x_data"]["name"], yaxis_title="Price" ,title="Spot Price")

      st.plotly_chart(price, use_container_width=True)
      st.plotly_chart(fig, use_container_width=True)
