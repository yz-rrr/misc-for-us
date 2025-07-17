# 0625作成（from 個数とDEV_年度.ipynb）
# combine_eiとcombine_srのあとにやること

import csv
import json
import os
import re
import ast
import numpy as np
import pandas as pd


def concat_ep_sr(ep_filename, sr_filename):

    filename = ep_filename
    df_ep = pd.read_csv(filename, dtype={"emoji_list_body": object, "position_list_body": object, 
                                    "emoji_list_title": object, "position_list_title": object, 
                                    "title": str, "年度": str, "通しＮｏ．": str, "body_combined": str})

    df_ep["emoji_list_body"] = [ast.literal_eval(d) for d in df_ep['emoji_list_body']]
    df_ep["position_list_body"] = [ast.literal_eval(d) for d in df_ep['position_list_body']]
    df_ep["emoji_list_title"] = [ast.literal_eval(d) for d in df_ep['emoji_list_title']]
    df_ep["position_list_title"] = [ast.literal_eval(d) for d in df_ep['position_list_title']]

    filename = sr_filename
    df_sr = pd.read_csv(filename, dtype=str)

    df_ep = df_ep.drop(['Unnamed: 0', 'Unnamed: 0.1'], axis=1)
    # , 'Unnamed: 0.1.1'
    df = pd.merge(df_sr, df_ep, on=['通しＮｏ．', '年度'])
    df = df.drop(['Unnamed: 0', 'Unnamed: 0.1'], axis=1)

    print(df.info())

    df.to_csv("./ep-sr_info_nendo2004-2010_0625.csv")


if __name__ == '__main__':
    ep_filename = "./ed_ei_2004-2010_0625重複削除.csv"
    sr_filename = "./sr_info_2004-2010.csv"
    concat_ep_sr(ep_filename=ep_filename, sr_filename=sr_filename)
