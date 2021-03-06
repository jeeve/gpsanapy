from time import time
import pandas as pd
from pandas.plotting import parallel_coordinates, andrews_curves
import matplotlib.pyplot as plt
from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.palettes import Inferno
import numpy as np
from scipy.stats import gaussian_kde

from utils import load_config
from gps_analysis import TraceAnalysis, Trace


def gkde(data, gridsize):
    """
    :param data: pd timeserie
    :return: x grid & gaussian kde series
    """

    bw = 1/data.std()
    x_grid = np.linspace(data.min(), data.max(), gridsize)
    gkde = gaussian_kde(data, bw_method=bw)
    gkde_pdf = gkde(x_grid)
    return (x_grid, gkde_pdf)


def build_crunch_df(df, result_types):
    if not result_types:
        return
    # df2 = df[df.description.isin(result_types)].pivot_table(
    #     values=["result"],
    #     index=["n"],
    #     columns=["description"],
    #     aggfunc=np.mean,
    #     dropna=True,
    # )
    # df2.result[result_type]
    df2 = pd.DataFrame(
        data={
            result_type: df[df.description == result_type].result
            for result_type in result_types
            if (df.description == result_type).any()
        }
    )
    return df2


def all_results_speed_density(all_results):
    """crunch data with all ranking results"""
    if all_results is None:
        return
    trace = Trace()
    result_types = [r for k,v in trace.ranking_groups.items() for r in v]
    # do not plot 0 results:
    all_results.astype({'result':'float64'}).dtypes

    # density plot:
    all_results2 = all_results.reset_index(drop=True)
    df = build_crunch_df(all_results2, result_types)
    p = figure(x_axis_label="speed (kn)")
    try:
        for result_type, color in zip(result_types, Inferno[len(result_types)]):
            data = df[result_type].dropna()
            x, pdf = gkde(data, 100)
            p.line(x, pdf, color=color, line_width=3, legend_label=f'gkde density of {result_type}')
    except Exception as e:
        print(e)

    return p


def bokeh_speed(gpsana_client):
    p = figure(x_axis_type="datetime", x_axis_label="time")
    dfs = pd.DataFrame(index=gpsana_client.ts.index)
    dfs["raw_speed"] = gpsana_client.raw_ts
    dfs.loc[dfs.raw_speed>55, "raw_speed"] = 55
    dfs["speed"] = gpsana_client.ts
    dfs["speed_no_doppler"] = gpsana_client.tsp
    dfs.loc[dfs.speed_no_doppler > 55, "speed_no_doppler"] = 55
    dfs = dfs.reset_index()
    source = ColumnDataSource(dfs)
    p.line(x='time', y='raw_speed', source=source, color='blue', line_width=2, legend_label='unfiltered raw speed')
    p.line(x='time', y='speed', source=source, color='red', legend_label = 'doppler speed')
    p.line(x='time', y='speed_no_doppler', source=source, color='orange', legend_label='positional speed')
    return p


def bokeh_speed_density(gpsana_client, s):

    xs = f"{int(10)}S"
    p = figure(x_axis_label="speed (kn)")
    dfs = pd.DataFrame(index=gpsana_client.ts.index)
    dfs["speed"] = gpsana_client.ts
    dfs["speed_xs"] = gpsana_client.ts.rolling(xs).mean()
    dfs = dfs.reset_index()
    dfs.dropna(inplace=True)

    x_grid_xs, pdf_xs = gkde(dfs.speed_xs, 200)
    x_grid, pdf = gkde(dfs.speed, 200)

    p.line(x_grid, pdf, color='blue', legend_label=f'gkde density of filtered max doppler speeds')
    p.line(x_grid_xs, pdf_xs, color='red', legend_label=f'gkde density of v{xs} speeds')

    return p


def compare_all_results_density(all_results, gpsana_client, result_types):
    if all_results is None:
        return
    # do not plot 0 results:
    all_results.astype({'result':'float64'}).dtypes

    # density plot:
    all_results2 = all_results.reset_index(drop=True)
    df = build_crunch_df(all_results2, result_types)
    results = build_crunch_df(gpsana_client.gpx_results, result_types)
    p = figure(x_axis_label='speed (kn)')

    #result = gpsana_client.gpx_results[gpsana_client.gpx_results.description.isin(result_types)].result
    #result_list = list(pd.Series.to_numpy(result))
    colors = Inferno[len(result_types)+1]
    for result_type, color in zip(result_types, colors):
        data = df[result_type].dropna()
        data = data[data>0]
        result = results[result_type].dropna()
        result = result[result>0]
        if len(data)>1 and len(results)>0:
            x, pdf = gkde(data, 100)
            h = pdf.max()
            p.line(x, pdf, color=color, line_width=3, legend_label=f'gkde density of {result_type}')
            for r in pd.Series.to_numpy(result):
                p.line([r, r], [0, h], color=color, line_width=2)
    # for r, c in zip(result_list, colors[1:]):
    #     p.line([r, r], [0, h], color=c, line_width=2)

    return p







def process_config_plot(all_results, config_plot_file):
    """deprecated"""
    if all_results is None:
        return

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(nrows=2, ncols=2)
    config_plot = load_config(config_plot_file)
    # do not plot 0 results:
    all_results.astype({'result':'float64'}).dtypes
    all_results.loc[all_results.result < 10, 'result'] = np.nan

    result_types = config_plot.get('distribution', [])
    # density plot:
    all_results2 = all_results.reset_index(drop=True)
    df = build_crunch_df(all_results2, result_types)
    df.plot.kde(ax=ax1)
    ax1.set_title("speed density")
    ax1.set_xlabel("speed (kn)")
    # parallel coordinates plot:
    all_results2 = all_results.set_index(pd.to_datetime(all_results.date))
    all_results2 = all_results2.set_index(all_results2.index.year)
    df = build_crunch_df(all_results2, result_types)
    df = df.reset_index()
    df0 = df.copy()
    parallel_coordinates(df, 'date', colormap="winter", ax=ax2)

    #andrews_curves(df, 'date', colormap="winter", ax=ax2)
    #cumulated
    result_types = config_plot.get('cumulated', [])
    all_results2 = all_results.set_index(pd.to_datetime(all_results.date))
    df = build_crunch_df(all_results2, result_types)
    df = df.resample('M').sum()
    df['cum_planning_distance>12'] = df['planning_distance>12'].cumsum()
    df.plot(ax=ax3)
    ax3.set_ylabel("distance (km)")
    # simple_plot
    result_types = config_plot.get('simple_plot', [])
    all_results2 = all_results.set_index(pd.to_datetime(all_results.date))
    df = build_crunch_df(all_results2, result_types)
    #df = df.resample('M').mean()
    df=df.reset_index()
    df.plot.scatter(x='date', y='Vmoy>12', ax=ax4)

    result_types = config_plot.get('distribution', [])
    fig, axx = plt.subplots(nrows=len(result_types))
    for i, result_type in enumerate(list(result_types)):
        data = {
            f"{result_type}_{year}": df0.loc[df0.date==year, result_type].reset_index(drop=True)
            for year in set(df0.date)
        }
        df2 = pd.DataFrame(data = data)
        df2.plot.kde(ax=axx[i])

def bokeh_plot(all_results):
    """deprecated"""
    all_results.astype({"result": "float64"}).dtypes

    all_results.loc[all_results.result < 10, "result"] = np.nan
    config_plot_file = None
    config_plot = load_config(config_plot_file)
    result_types = config_plot.get("simple_plot", [])
    all_results2 = all_results.set_index(pd.to_datetime(all_results.date))
    df = build_crunch_df(all_results2, result_types)
    df = df.reset_index()
    source = ColumnDataSource(df)
    tool = HoverTool(
        formatters={"@date": "datetime"},
        tooltips=[
            ("name", "$name"),
            ("date", "@date{%Y%m%d}"),
            ("(x, y)", "($x, $y)"),
            ("value", "@date"),
        ],
        mode="vline",
    )
    p = figure(x_axis_type="datetime", x_axis_label="date", y_axis_label="vmoy>12")
    p.add_tools(tool)
    p.circle(
        x="date",
        y="Vmoy>12",
        size=10,
        source=source,
        color="red",
        name="average speed history",
    )

    # p.xaxis.axis_label = "date"
    # p.yaxis.axis_label = "vmoy>12"

    return p
    # show(p)