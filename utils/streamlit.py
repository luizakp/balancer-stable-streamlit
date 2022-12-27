import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

class Streamlit:
  def initiate_session_state(self, key, value):
    if key not in st.session_state:
      st.session_state[key] = value
    else: 
      st.session_state[key] = value

  def pool_chart(self, df, current_transaction, new_transaction, x_data_name, y_data):
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

    fig.update_layout(xaxis_title=st.session_state["x_data"]["name"], yaxis_title=y_data["name"], title="Pool", hovermode='x unified')
    
    return fig
  
  def spot_price_chart(self, df, current_transaction, new_transaction, x_data_name):
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

    price.update_layout(xaxis_title=st.session_state["x_data"]["name"], yaxis_title="Price" ,title="Spot Price", hovermode='x unified')

    return price
  
  def depth_cost_chart(self, current_stable_swape, new_stable_swape, base_amp, new_amp, x_data, type_token_sell):
    base_x = float(x_data["balance"])
    x_data_name = x_data["name"]
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

    return depth_fig

  def price_impact_kpi(self, tab_col1, tab_col2, current_stable_swape, current_transaction, new_stable_swape, new_transaction, y_data, base_amp, new_amp, type_token_sell):
    type_token_buy = y_data["name"]
    
    #this way we make calculations with decimals
    current_initial_spot_price = current_stable_swape.calculate_spot_price(st.session_state["x_data"]["name"], y_data["name"], current_transaction['transaction_sell'][0])
    current_final_spot_price = current_stable_swape.calculate_spot_price(st.session_state["x_data"]["name"], y_data["name"], current_transaction['transaction_sell'][1])
    current_price_impact = current_stable_swape.calculate_price_impact(current_initial_spot_price,current_final_spot_price)
    current_transaction['spot_price'] = [float(current_initial_spot_price),float(current_final_spot_price)]

    #this way we make calculations with decimals
    new_initial_spot_price = new_stable_swape.calculate_spot_price(st.session_state["x_data"]["name"], y_data["name"], new_transaction['transaction_sell'][0])
    new_final_spot_price = new_stable_swape.calculate_spot_price(st.session_state["x_data"]["name"], y_data["name"], new_transaction['transaction_sell'][1])
    new_price_impact = new_stable_swape.calculate_price_impact(new_initial_spot_price,new_final_spot_price)
    new_transaction['spot_price'] = [float(new_initial_spot_price),float(new_final_spot_price)]

    price_delta = float(100-((new_transaction['price']/current_transaction['price'])*100))
    price_impact_delta = float(100-((new_price_impact/current_price_impact)*100))

    new_amount_token_buy = new_transaction['amount_token_buy']
    current_amount_token_buy = current_transaction['amount_token_buy']

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
      tab_col1.subheader(f'Amp factor {base_amp:.5f}')
      tab_col1.write(f'Will receive {current_amount_token_buy:.5f} of {type_token_buy}')
      tab_col1.metric(label=f"Price of {type_token_buy} for 1 {type_token_sell}", value=float(current_transaction['price']))
      tab_col1.metric(label="Price Impact", value=float(current_price_impact))