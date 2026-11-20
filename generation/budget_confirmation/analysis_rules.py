import math

def choose_combination(single_success,dual_success,single_cost,dual_cost):
    if single_success==0:return dict(recommendation='D' if dual_success else 'unconfirmed',reason='only_dual_succeeds' if dual_success else 'neither_strategy_succeeds')
    if dual_success>single_success and dual_cost<=1.2*single_cost:return dict(recommendation='D',reason='higher_yield_within_20pct_cost')
    if dual_success==single_success and dual_cost<=.8*single_cost:return dict(recommendation='D',reason='same_yield_at_least_20pct_cheaper')
    return dict(recommendation='S',reason='simpler_same_yield' if dual_success==single_success else 'dual_lower_yield' if dual_success<single_success else 'dual_gain_costs_more_than_20pct')

def wilson(success,n):
    if not n:return None
    z=1.959963984540054;p=success/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,center-half),min(1,center+half)]
