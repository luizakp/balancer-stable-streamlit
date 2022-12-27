import decimal
import numpy as np
from functools import reduce
from abc import ABC, abstractmethod, abstractproperty
from balancerv2cad.StableMath import StableMath


class MarketMaker(ABC):
  def __init__(self, **kwargs):
    self.constant = self.get_constant(**kwargs)
  
  @abstractmethod
  def get_constant(self):
    pass

  @abstractmethod
  def calculate_y(self):
    pass
  
  @abstractmethod
  def calculate_spot_price(self):
    pass
  
  def define_binary_sell_buy(self, type_token_sell, x_data, y_data):
    if x_data["name"] == type_token_sell:
      namesData = {
        'type_token_buy': y_data["name"],
        'initial_amount_sell': float(x_data["balance"]),
        'initial_amount_buy': float(y_data["balance"]),
      }
      return namesData
    else:
      namesData = {
        'type_token_buy': x_data["name"],
        'initial_amount_sell': float(y_data["balance"]),
        'initial_amount_buy': float(x_data["balance"]),
      }
      return namesData

class BinaryMarketMaker(MarketMaker):
  def calculate_trade(self, initial_amount_sell, initial_amount_buy, amount_token_sell): 
    initial_amount_sell = float(initial_amount_sell)
    initial_amount_buy = float(initial_amount_buy)
    amount_token_sell = float(amount_token_sell)
    
    final_amount_sell = initial_amount_sell+amount_token_sell
    final_amount_buy = self.calculate_y(final_amount_sell)
    amount_token_buy = initial_amount_buy-final_amount_buy
    price = amount_token_buy/amount_token_sell

    transaction = {
      'amount_token_buy': amount_token_buy,
      'price': price,
      'transaction_sell': [initial_amount_sell,final_amount_sell],
      'transaction_buy': [initial_amount_buy,final_amount_buy],
      'label': ['Before the trade', 'After the trade']
    }

    return transaction
    
class LinearInvariant(BinaryMarketMaker):
  def get_constant(self, x, y):
    return x+y
  
  def calculate_y(self, x):
    return self.constant - x
  
  def calculate_spot_price(self):
    return 1

class Uniswap(BinaryMarketMaker):
  def get_constant(self, x, y):
    return x*y
  
  def calculate_y(self, x):
    return self.constant / x
  
  def calculate_spot_price(self, x):
    return self.constant / (x**2)
  
  def calculate_value_to_spot_price(self, initial_value, price):
    new_value = (self.constant / price) ** (1/2)
    return abs(initial_value - new_value)

class StableSwapBinary(BinaryMarketMaker):
  def __init__(self, **kwargs):
    self.amp = kwargs["amp"]
    super().__init__(**kwargs)

  def get_constant(self, x, y, amp):
      a = 1/4
      b = amp
      c = -1 * ((amp * (x+y)) + (x*y))
      delta = ((b**2) - (4*a*c))**(1/2)
      return (-b + delta)/(2*a)

  def calculate_y(self, x):
    first_part = self.amp * self.constant + ((self.constant/2)**2) - self.amp*x
    second_part = 1/(self.amp+x)
    return first_part * second_part

  def calculate_spot_price(self, x):
    part1 = 1/(self.amp+x)
    part21 = self.amp
    part221 = (self.amp*self.constant)+((self.constant**2)*0.25)-(self.amp*x)
    part222 = 1/(self.amp+x)
    return part1*(part21+(part221*part222))

  def calculate_value_to_spot_price(self, initial_value, price):
    part111 = 4*(self.amp**2)*price
    part112 = 4*self.amp*price*self.constant
    part113 = price*(self.constant**2)
    part11 = (part111+part112+part113)**(1/2)
    part12 = 2*self.amp*price
    part1 = part11-2*self.amp*price
    part2 = 2*price
    new_value = part1/part2
    return abs(initial_value-new_value)


class StableSwap(MarketMaker):
  def __init__(self, **kwargs):
    self.amp = decimal.Decimal(kwargs["amp"])
    self.names = kwargs["names"]
    self.balances = [decimal.Decimal(x) for x in kwargs["balances"]]
    super().__init__()
  
  def _get_constant_balances(self, x_name, y_name):
    index_x = self.names.index(x_name)
    index_y = self.names.index(y_name)
    constant_balances = [self.balances[i] for i in range(len(self.balances)) if i not in [index_x, index_y]]
    return constant_balances

  def _calculate_c1_c2(self, D, A, n, S, P):
    c1 = (D/(A*(n**n))) + S - D
    c2 = -(D**(n+1)) / (A*(n**(2*n))*P)
    return c1, c2

  def get_constant(self):
    return StableMath.calculateInvariant(self.amp, self.balances)

  def calculate_y(self, x_name, y_name, x):
    balances_input = self.balances[:] # copy balances
    balances_input[self.names.index(x_name)] = decimal.Decimal(x)
    return StableMath.getTokenBalanceGivenInvariantAndAllOtherBalances(self.amp, balances_input, self.constant, self.names.index(y_name))
  
  def calculate_spot_price(self, x_name, y_name, x):
    constant_balances = self._get_constant_balances(x_name, y_name)
    # define initial parameters
    n = len(self.names)
    if n > 2: 
      S = sum(constant_balances)
      P = reduce(lambda x, y: x*y, constant_balances)
    else:
      S = 0
      P = 1
    D = self.constant
    A = self.amp
    x = decimal.Decimal(x)

    # calculate aux values
    c1, c2 = self._calculate_c1_c2(D, A, n, S, P)
    b = c1+x
    c = c2/x
    dc = -c2/(x**2)

    # calculate spot price
    num = b-(2*dc)
    in_root = (b**2) - 4*c
    den = 2*(in_root**decimal.Decimal(0.5))
    dy = (num/den) - decimal.Decimal(0.5)
    return -dy
  
  def calculate_value_to_spot_price(self, x_name, y_name, price):
    constant_balances = self._get_constant_balances(x_name, y_name)
    price = decimal.Decimal(price)

    # define initial parameters
    n = len(self.names)
    if n > 2:
      S = sum(constant_balances)
      P = reduce(lambda x, y: x*y, constant_balances)
    else:
      S = 0
      P = 1
    D = self.constant
    A = self.amp
    dy = decimal.Decimal(-price)
    initial_x = self.balances[self.names.index(x_name)]

    # calculate aux values
    c1, c2 = self._calculate_c1_c2(D, A, n, S, P)
    f6 = 4*(dy**2)+(4*dy)
    f5 = (8*c1*(dy**2))+(8*c1*dy)
    f4 = (4*(c1**2)*(dy**2))+(4*(c1**2)*dy)
    f3 = (-16*c2*(dy**2)) - (16*c2*dy) - 8*c2
    f2 = -4*c1*c2
    f1 = 0
    f0 = -4*(c2**2)
    
    # calculate roots and find closer solution
    roots = np.roots([f6, f5, f4, f3, f2, f1, f0])
    possible_results = [abs(decimal.Decimal(r.real)-initial_x) for r in roots if r.imag==0]
    return min(possible_results)
  
  def calculate_trade(self, x_name, y_name, amount):
    amount = decimal.Decimal(amount)
    output = StableMath.calcOutGivenIn(self.amp, self.balances, self.names.index(x_name), self.names.index(y_name), amount)
    
    initial_x = self.balances[self.names.index(x_name)]
    initial_y = self.balances[self.names.index(y_name)]
    final_x = initial_x + amount
    final_y = initial_y - output
    price = output/amount

    transaction = {
      'amount_token_buy': output,
      'price': price,
      'transaction_sell': [initial_x, final_x],
      'transaction_buy': [initial_y, final_y],
      'label': ['Before the trade', 'After the trade']
    }

    return transaction

  def calculate_price_impact(self,initial_spot_price, final_spot_price):
    return ((initial_spot_price-final_spot_price)/initial_spot_price)*100
