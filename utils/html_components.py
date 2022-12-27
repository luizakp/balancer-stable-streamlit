import streamlit.components.v1 as components

class Components():
  def balance_container_as_text(self, token_data, total_amount_pool):
    balance = float(token_data["balance"])
    return f"""
        <div class="bg-[#001e3c] text-white flex flex-col justify-center items-center w-fit p-5">
          <p>Balance of
            <span class="font-bold">{token_data["name"]}</span>
          :</p>
          <p class="text-3xl">{balance:.2f}</p> 
          <p> {(balance/total_amount_pool)*100:.2f}% of the pool</p>
        </div>
      """

  def binary_balance_conteiner(self, token_data_x, token_data_y):
    total_amount_pool = float(token_data_x["balance"]) + float(token_data_y["balance"])
    return components.html(
      f"""
        <script src="https://cdn.tailwindcss.com"></script>
        <div class="flex justify-between">
          {self.balance_container_as_text(token_data_x,total_amount_pool)}
          {self.balance_container_as_text(token_data_y,total_amount_pool)}
        </div>
      """
    )
  
  @staticmethod
  def error_container(title, message):
    return components.html(
      f"""
        <script src="https://cdn.tailwindcss.com"></script>
        <div class="bg-[#f88379] flex-col justify-left ">
          <h1 class="text-3xl m-5">{title}</h1>
          <p class="text-xl m-5">{message}</p>
        </div>
      """
    )