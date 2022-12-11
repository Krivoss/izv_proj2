#!/usr/bin/env python3.9
# coding=utf-8

from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np
import zipfile
from os.path import exists, dirname
from os import makedirs
import urllib.request


# muzete pridat libovolnou zakladni knihovnu ci knihovnu
# predstavenou na prednaskach dalsi knihovny pak na dotaz

# Ukol 1: nacteni dat ze ZIP souboru
def load_data(filename: str) -> pd.DataFrame:
    # tyto konstanty nemente, pomuzou vam pri nacitani
    headers = ["p1", "p36", "p37", "p2a", "weekday(p2a)",
               "p2b", "p6", "p7", "p8", "p9", "p10", "p11", "p12", "p13a",
               "p13b", "p13c", "p14", "p15", "p16", "p17", "p18",
               "p19", "p20", "p21", "p22", "p23", "p24", "p27", "p28",
               "p34", "p35", "p39", "p44", "p45a", "p47", "p48a",
               "p49", "p50a", "p50b", "p51", "p52", "p53", "p55a",
               "p57", "p58", "a", "b", "d", "e", "f", "g", "h", "i",
               "j", "k", "l", "n", "o", "p", "q", "r", "s", "t", "p5a"]

    # def get_dataframe(filename: str, verbose: bool = False) -> pd.DataFrame:
    regions = {
        "PHA": "00",
        "STC": "01",
        "JHC": "02",
        "PLK": "03",
        "ULK": "04",
        "HKK": "05",
        "JHM": "06",
        "MSK": "07",
        "OLK": "14",
        "ZLK": "15",
        "VYS": "16",
        "PAK": "17",
        "LBK": "18",
        "KVK": "19",
    }

    df = pd.DataFrame()
    with zipfile.ZipFile(filename, "r") as root_zf:
        for year_file in root_zf.infolist():
            with zipfile.ZipFile(root_zf.open(year_file), "r") as year_zf:
                for file in year_zf.infolist():
                    if file.filename == "CHODCI.csv" or file.file_size == 0:
                        continue
                    with year_zf.open(file) as f:
                        read_data = pd.read_csv(
                            f, encoding="cp1250", delimiter=";",
                            low_memory=False, names=headers, decimal=",")
                        num = file.filename[0:2]
                        read_data["region"] = list(regions.keys())[
                            list(regions.values()).index(num)]
                        df = pd.concat([df, read_data])
    return df


# Ukol 2: zpracovani dat
def parse_data(df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    parsed_df = pd.DataFrame(df, copy=True)

    parsed_df.rename(columns={"p2a": "date"}, inplace=True)
    parsed_df["date"] = pd.to_datetime(parsed_df["date"])

    category = ["k", "l", "o", "p", "q"]
    parsed_df[category] = parsed_df[category].astype("category")

    not_numeric = ["date", "region", "h", "i"] + category
    to_numeric = parsed_df.drop(not_numeric, axis=1).apply(
        pd.to_numeric, errors="coerce")
    parsed_df[to_numeric.columns] = to_numeric

    parsed_df.drop_duplicates(subset=["p1"], inplace=True)

    if verbose:
        orig_size = df.memory_usage(
            index=True, deep=True).sum() / np.power(10, 6)
        new_size = parsed_df.memory_usage(
            index=True, deep=True).sum() / np.power(10, 6)
        print(f"orig_size={orig_size:.1f} MB")
        print(f"new_size={new_size:.1f} MB")

    return parsed_df


# Ukol 3: počty nehod v jednotlivých regionech podle viditelnosti
def plot_visibility(df: pd.DataFrame, fig_location: str = None,
                    show_figure: bool = False):
    sel_regions = ["PHA", "STC", "PLK", "JHM"]
    df = df.copy(deep=True)
    df = df.loc[df["region"].isin(sel_regions)]

    types_list = ["den: viditelnost nezhoršená", "den: viditelnost zhoršená",
                  "noc: viditelnost nezhoršená", "noc: viditelnost zhoršená"]
    types_dic = {
        1: types_list[0],
        2: types_list[1],
        3: types_list[1],
        4: types_list[2],
        5: types_list[3],
        6: types_list[2],
        7: types_list[3]
    }
    df.loc[:, "p19"] = df.loc[:, "p19"].replace(types_dic)

    df = (df.groupby(["region", "p19"]).agg({"p1": "count"})).reset_index()

    sns.set_style("darkgrid")
    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(8, 6))
    axes = axes.flatten()
    for i in range(4):
        sns.barplot(ax=axes[i],
                    data=df.loc[df["p19"] == types_list[i]],
                    x="region",
                    y="p1")
        axes[i].set_title(types_list[i])
        axes[i].set(ylabel="Počet nehod", xlabel="Kraj")

    axes[0].set(xlabel="")
    axes[1].set(ylabel="", xlabel="")
    axes[3].set(ylabel="")
    fig.tight_layout()

    if fig_location:
        plt.savefig(fig_location)
    if show_figure:
        plt.show()


# Ukol 4: druh srážky jedoucích vozidel
def plot_direction(df: pd.DataFrame, fig_location: str = None,
                   show_figure: bool = False):
    df = df.copy(deep=True)
    sel_regions = ["PHA", "STC", "PLK", "JHM"]
    df = df.loc[df["region"].isin(sel_regions)]

    collision_types = {
        1: "čelní",
        2: "boční",
        3: "boční",
        4: "zezadu",
        0: "nepřichází v úvahu"
    }
    df = df[df["p7"] != 0]

    df["p7"] = df["p7"].replace(collision_types)

    df["month"] = df["date"].dt.month

    df = (df.groupby(["region", "month", "p7"]).agg(
        {"p1": "count"})).reset_index()
    sns.set_style("darkgrid")
    g = sns.catplot(data=df,
                    x="month",
                    y="p1",
                    hue="p7",
                    kind="bar",
                    col="region",
                    sharey=False,
                    sharex=False,
                    col_wrap=2,
                    aspect=1.4,
                    legend=True,
                    legend_out=True,
                    errorbar=None)
    g.set_titles("Kraj: {col_name}")
    g.set_xlabels("Měsíc")
    g.set_ylabels("Počet nehod")
    g.legend.set(title="Druh srážky")
    g.tight_layout()

    if fig_location:
        plt.savefig(fig_location)
    if show_figure:
        plt.show()

# Ukol 5: Následky v čase


def plot_consequences(df: pd.DataFrame, fig_location: str = None,
                      show_figure: bool = False):
    df = df.copy(deep=True)
    sel_regions = ["PHA", "STC", "PLK", "JHM"]
    df = df.loc[df["region"].isin(sel_regions)]
    df = df.loc[df["date"].dt.year < 2022]

    accident_results = {
        "p13a": "usmrcení",
        "p13b": "těžké zranění",
        "p13c": "lehké zranění"
    }

    return
    df = (df.groupby(["region", "date"]).agg({"p1": "count"})).reset_index()
    df = (df.groupby(pd.Grouper(key="date", freq="MS")).agg(
        {"p1": "count"})).reset_index()
    #

    sns.lineplot(data=df,
                 x="date",
                 y="p1",
                 hue="accident_results",
                 col="region"
                 )

    if fig_location:
        plt.savefig(fig_location)
    if show_figure:
        plt.show()


if __name__ == "__main__":
    # zde je ukazka pouziti, tuto cast muzete modifikovat podle libosti
    # skript nebude pri testovani pousten primo, ale budou volany konkreni
    # funkce.
    file_name = "parsed_df.csv"
    new_load = False
    if new_load:
        df = load_data("data/data.zip")
        df2 = parse_data(df, True)
        df2.to_pickle(file_name)
    else:
        df2 = pd.read_pickle(file_name)

    # plot_visibility(df2, "01_visibility.png", True)
    # plot_direction(df2, "02_direction.png", True)
    plot_consequences(df2, "03_consequences.png", True)


# Poznamka:
# pro to, abyste se vyhnuli castemu nacitani muzete vyuzit napr
# VS Code a oznaceni jako bunky (radek #%%% )
# Pak muzete df jednou nacist a dale ladit jednotlive funkce
# Pripadne si muzete vysledny dataframe ulozit nekam na disk (pro ladici
# ucely) a nacitat jej naparsovany z disku
