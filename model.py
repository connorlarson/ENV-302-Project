import numpy as np
from numpy import random as rd
import matplotlib.pyplot as plt
import csv

# import configuration VERY IMPORTANT
from hawaii_high import *

# random seed
rd.seed(2022)

# how long should simulation be
# DAYS = (365 * 20)  # number of days
# steps_per_day = 24  # steps per day

# time-related parameters
dt = 1 / steps_per_day  # time step length in 1/days
N = DAYS * steps_per_day  # total number of iterations
time_list = [dt * i for i in range(N)]

# rainfall metrics from Google (imperial units)
# yearly_rainfall = 1194  # average yearly rainfall in mm
# rainy_days = 102  # average rainy days per year (Princeton: 102)
DAYS_IN_YEAR = 365

# "Poisson" distribution (is actually a binomial approximation)
p_rainy = dt * rainy_days / DAYS_IN_YEAR  # probability a day is raining
exp_rain = yearly_rainfall / rainy_days  # expected rainfall on rainy days


# Exponential distribution inverse cdf
def inv_exp(p, mu):
    return -1 * np.log(1 - p) * mu


# function to get list of rainfall amounts
def sim_rain(periods=N):
    # list of rainfall metrics
    rain_history = []

    # Simulate rainy days
    for i in range(periods):
        rainy = (rd.uniform() < p_rainy)
        rain = 0

        if rainy:
            rain = inv_exp(rd.uniform(), exp_rain)

        rain_history.append(rain)

    return rain_history


# plot daily and cumulative rainfall
def plot_rain(rainfall, days=N):
    # plot daily rainfall
    x = time_list[:days * steps_per_day]
    y = rainfall[:days * steps_per_day]

    plt.plot(x, y)
    plt.title("Rainfall Events in " + location)
    plt.xlabel("Day of year")
    plt.ylabel("Millimeters of rain")
    plt.show()
    plt.close()

    # plot cumulative rainfall
    # plt.plot(time_list, [sum(rainfall[:i]) for i in range(len(rainfall))])
    # plt.title("Cumulative Rainfall in Princeton, NJ")
    # plt.xlabel("Day of year")
    # plt.ylabel("Inches of rain")
    # plt.show()
    # plt.close()


# %%

# soil moisture box model setup
# parameters (all quantities normalized per unit area)
# Z = 0.8 * 1000  # depth of the soil in mm
# n = 0.4  # porosity
# s_h = 0.02  # hygroscopic point
# s_w = 0.065  # wilting point
# s_ast = 0.17  # water stress point
# s_fc = 0.3  # field capacity
# E_max = 0.9  # max evaporation in/day
# T_max = 3.6  # max transpiration in/day
# b = 0.2  # soil porosity index
# K_s = 1.1  # saturated hydraulic conductivity in/day

# infiltration (h is storm rainfall)
I = lambda s, h: min(h, n * Z * (1 - s))


# evaporation
def E(s):
    if s < s_h:
        return 0
    elif s < s_w:
        return E_max * (s - s_h) / (s_w - s_h)
    else:
        return E_max


# transpiration
def T(s):
    if s < s_w:
        return 0
    elif s < s_ast:
        return T_max * (s - s_w) / (s_ast - s_w)
    else:
        return T_max


# leakage
def L(s):
    beta = 2 * b + 4

    if s < s_fc:
        return 0
    else:
        return K_s * (np.exp(beta * (s - s_fc)) - 1) / (np.exp(beta * (1 - s_fc)) - 1)


# function to plot water loss curve
def plot_water_loss():
    x_axis = [i / 100 for i in range(100)]
    y_axis = [L(i / 100) + E(i / 100) + T(i / 100) for i in range(100)]
    plt.plot(x_axis, y_axis)
    plt.title("Total Soil Losses (Evapotranspiration + Leakage)")
    plt.xlabel("Relative Soil Moisture")
    plt.ylabel("Losses (inches per day)")
    plt.show()
    plt.close()


# %%

# forward euler time step for soil moisture
def sim_soil_moisture(rainfall):
    s = s_init
    series = []

    for t in range(len(rainfall)):
        ds = I(s, rainfall[t]) - (dt * (E(s) + T(s) + L(s)))
        ds /= (n * Z)
        s += ds
        series.append(s)

    return series


# plot soil moisture
def plot_soil_moisture(soil_moisture, days=N):
    plt.plot(time_list[:days * steps_per_day], soil_moisture[:days * steps_per_day])
    plt.title("Relative Soil Moisture")
    plt.xlabel("Day")
    plt.ylabel("Relative Soil Moisture")
    plt.show()
    plt.close()


# %%

# function to relate decay to soil moisture
def f_d(s):
    if s < s_fc:
        return s / s_fc
    else:
        return s_fc / s


# function to plot soil moisture dependence
def plot_moisture_dependence():
    x_axis = [i / 100 for i in range(100)]
    y_axis = [f_d(i / 100) for i in range(100)]
    plt.plot(x_axis, y_axis)
    plt.title("Dependence of Decomposition on Soil Moisture")
    plt.xlabel("Relative Soil Moisture")
    plt.ylabel("Effect on Decomposition")
    plt.show()
    plt.close()


# %%
# carbon box model setup (metric units)

# parameters
# ADD = 1.5  # litterfall in gC per day*m^2
# k_d = 8.5 * 10 ** (-3)
# k_l = 6.5 * 10 ** (-5)
# k_h = 2.5 * 10 ** (-6)
# r_h = 0.25
# r_r = 0.6

# initial values (porporato et al.)
# C_h_init = 8500
# C_b_init = 80
# C_l_init = 1200


# functions
def BD(C_l, C_h, C_b, s):
    return k_d * C_b


def DEC_l(C_l, C_h, C_b, s):
    return f_d(s) * k_l * C_b * C_l


def DEC_h(C_l, C_h, C_b, s):
    return f_d(s) * k_h * C_b * C_h


def dC_l(C_l, C_h, C_b, s):
    return ADD + BD(C_l, C_h, C_b, s) - DEC_l(C_l, C_h, C_b, s)


def dC_h(C_l, C_h, C_b, s):
    return r_h * DEC_l(C_l, C_h, C_b, s) - DEC_h(C_l, C_h, C_b, s)


def dC_b(C_l, C_h, C_b, s):
    return (1 - r_h - r_r) * DEC_l(C_l, C_h, C_b, s) + (1 - r_r) * DEC_h(C_l, C_h, C_b, s) - BD(C_l, C_h, C_b, s)


def dC(C_l, C_h, C_b, s):
    return ADD - r_r * DEC_l(C_l, C_h, C_b, s) - r_r * DEC_h(C_l, C_h, C_b, s)


# euler box model for carbon
def sim_carbon(s, C_l=C_l_init, C_h=C_h_init, C_b=C_b_init):
    # time series for carbon
    C_l_series = []
    C_h_series = []
    C_b_series = []

    for t in range(len(s)):
        d = [dC_l(C_l, C_h, C_b, s[t]), dC_h(C_l, C_h, C_b, s[t]), dC_b(C_l, C_h, C_b, s[t])]

        C_l += d[0] * dt
        C_h += d[1] * dt
        C_b += d[2] * dt

        C_l_series.append(C_l)
        C_h_series.append(C_h)
        C_b_series.append(C_b)

    return {"Litter": C_l_series, "Humus": C_h_series, "Biomass": C_b_series}


# plot carbon levels
def plot_carbon(C, pool='ALL'):
    y = []

    if pool == 'ALL':
        for box in C:
            y = C[box]
            x = time_list
            plt.plot(x, y, label=box)

    else:
        y = C[pool]
        x = time_list
        plt.plot(x, y, label=pool)
        plt.title("Carbon Content")
        plt.legend()

    plt.xlabel("Day")
    plt.ylabel("Carbon (gC / (m^3)")
    plt.ylim(ymin=0)
    plt.ylim(ymax=1.2 * max(y))
    plt.show()
    plt.close()


# %%
# type code to run below (or in console)
h = sim_rain()
s = sim_soil_moisture(h)
C = sim_carbon(s)

plot_rain(h, days=365)
plot_soil_moisture(s, days=365)
plot_carbon(C, 'Litter')
plot_carbon(C, 'Humus')
plot_carbon(C, 'Biomass')

# %%
# export to CSV for analysis
