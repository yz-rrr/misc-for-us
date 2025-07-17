import ast

import os
import re

import datetime

import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt

# plt.rcParams['font.family'] = 'Hiragino Sans'


def f_datetime_year(x):
    # 日付型じゃないデータをNaNにしてやるため
    
    try:
        d = datetime.datetime.strptime(x, '%Y%m%d')
    except Exception as e:
        print(x)
        return None
    
    try:
        y = d.year
    except Exception as e:
        print(d)
        return None
    
    return int(y)


def make_MCN(df):

    MC_list = list(set(df['sender_携帯会社名']) | set(df['receiver_携帯会社名']))
    MC_list_notU = [s for s in MC_list if s != '不明']
    print(MC_list_notU)
    df['MCN同異'] = df.apply(lambda row: '不明' if (row['sender_携帯会社名'] == '不明' or row['receiver_携帯会社名'] == '不明') else ('同' if row['sender_携帯会社名'] == row['receiver_携帯会社名'] else '異'), axis=1)

    return df

def make_shori(nendo_filename, output_filename):
    # filename = "ep-sr_info_nendo2004-2010_0625.csv"
    df = pd.read_csv(nendo_filename, dtype={"emoji_list_body": object, "position_list_body": object,  
                                  "emoji_list_title": object, "position_list_title": object, 
                                  "title": str, "年度": str, "通しＮｏ．": str, "body_combined": str, "送受信主体者携帯会社名": str, 
                                  "相手ID": str, "送受信年月日": str, "sender_生年月日": str, "receiver_生年月日": str})

    df = make_MCN(df)
    AAA = df["送受信年月日"].replace(re.compile(r"\s"), '', regex=True)

    # 前処理（データクリーニング）
    AAA = AAA.replace(re.compile(r"１"), '1', regex=True)
    # AAA = AAA.replace('200600907', '20060907', regex=True)
    AAA = AAA.str.strip()

    # BBB = AAA.replace(re.compile(r"１"), '1', regex=True)
    BBB = AAA.replace(re.compile(r"[0-9]{8}"), '', regex=True)

    print(BBB.value_counts())
    series_years = AAA.apply(f_datetime_year)
    # series_years = series_years.astype(int)
    # series_years = pd.to_numeric(series_years, errors="coerce")
    # ただのintだと欠損値があってエラーになるのでInt64に
    series_years = series_years.astype("Int64")

    series_years.value_counts()
    print(AAA[series_years.isna() == True])
    df['送受信year'] = series_years

    df.to_csv(output_filename, index=False)


if __name__ == '__main__':
    nendo_filename = "./ep-sr_info_nendo2004-2010_0625.csv"
    output_filename = "./ep-sr-year_info_nendo2004-2010_0625.csv"
    make_shori(nendo_filename, output_filename)
