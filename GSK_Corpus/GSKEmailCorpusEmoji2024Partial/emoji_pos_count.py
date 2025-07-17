import ast

import os
import re

import numpy as np
import pandas as pd
# import matplotlib.pyplot as plt

#plt.rcParams['font.family'] = 'Hiragino Sans'


def culc_count_emoji(df):
    
    all_emoji_dict = {}

    # 本文
    for index, row in df.iterrows():
        emoji_list = row['emoji_list_body']

        for emoji in emoji_list:
                all_emoji_dict.setdefault(emoji, [0,0])
                all_emoji_dict[emoji][0] += 1

    # 件名
    for index, row in df.iterrows():
        emoji_list = row['emoji_list_title']
        
        for emoji in emoji_list:
                # print("aru")
                all_emoji_dict.setdefault(emoji, [0,0])
                all_emoji_dict[emoji][1] += 1
                
    return all_emoji_dict
  

def culc_count_emoji_in_pos(df, target_pos_list=['l0', 'l1']):
    
    pos_emoji_dict = {}

    # 本文
    for index, row in df.iterrows():
        emoji_list = row['emoji_list_body']
        position_list = row['position_list_body']
        for (emoji, position) in zip(emoji_list, position_list):
            if position in target_pos_list:
                pos_emoji_dict.setdefault(emoji, [0,0])
                pos_emoji_dict[emoji][0] += 1

    # 件名
    for index, row in df.iterrows():
        emoji_list = row['emoji_list_title']
        position_list = row['position_list_title']
        for (emoji, position) in zip(emoji_list, position_list):
            if position in target_pos_list:
                pos_emoji_dict.setdefault(emoji, [0,0])
                pos_emoji_dict[emoji][1] += 1
                
    return pos_emoji_dict
    
    
def culc_and_save_emoji_pos_freq(df, target_pos_list):
    
    pos_emoji_dict = culc_count_emoji_in_pos(df, target_pos_list)
    
    temp_list = []

    temp_list = [[item[0], item[1][0], item[1][1]] for item in list(sorted(pos_emoji_dict.items()))]

    # df_f_emoji_dict= pd.DataFrame(list(sorted(f_emoji_dict.items())), columns= ['emoji', 'count'])

    df_result= pd.DataFrame(temp_list, columns= ['emoji', 'count_body', 'count_title'])
    df_result.to_csv("./data/"+ "-".join(target_pos_list) + "_emoji_dict_body-title.csv", mode='w', index=False)
    
    
def get_data_df():
    
    filename = "./data/ep-sr-year_info_nendo2004-2010.csv"
    df = pd.read_csv(filename, dtype={"emoji_list_body": object, "position_list_body": object, 
                                      "emoji_list_title": object, "position_list_title": object, 
                                      "title": str, "年度": str, "通しＮｏ．": str, "body_combined": str, "送受信主体者携帯会社名": str, 
                                      "相手ID": str, "送受信年月日": str, "sender_生年月日": str, "receiver_生年月日": str})
    df["emoji_list_body"] = [ast.literal_eval(d) for d in df['emoji_list_body']]
    df["position_list_body"] = [ast.literal_eval(d) for d in df['position_list_body']]
    df["emoji_list_title"] = [ast.literal_eval(d) for d in df['emoji_list_title']]
    df["position_list_title"] = [ast.literal_eval(d) for d in df['position_list_title']]
    df['送受信year'] = df['送受信year'].astype("Int64")

    return df

def save_including_pos(df, target_pos_list):
    
    for pos in target_pos_list:
        df_incl_pos = df[df['position_list_body'].apply(lambda x: pos in x)]
        df_incl_pos['body_combined'].to_csv("./data/body_incl_pos_" + pos + ".csv")
        df_incl_pos = df[df['position_list_title'].apply(lambda x: pos in x)]
        df_incl_pos['title'].to_csv("./data/title_incl_pos_" + pos + ".csv")

    return True


if __name__ == '__main__':
    
    df = get_data_df()
    # culc_and_save_emoji_pos_freq(df, ['l1'])
    save_including_pos(df, ['l1'])
    
