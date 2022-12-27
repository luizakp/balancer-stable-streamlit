import streamlit.components.v1 as components

class Components():  
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