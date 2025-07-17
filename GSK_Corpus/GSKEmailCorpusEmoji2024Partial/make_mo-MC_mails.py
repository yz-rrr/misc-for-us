
import csv
import json
import os
import re
import numpy as np
import pandas as pd

# 年度，通しＮｏ．,
# 年度	通しＮｏ．	送受信主体者生年月日	出身地	出身地（国）	性別	送受信主体者携帯会社名
# 送信／受信
# 相手携帯会社名	相手ＩＤ	相手生年月日	相手出身地	相手出身地（国）	相手性別	相手親密度
# 	内／外	送受信年月日
# 送受信主体者携帯会社名,送信／受信,相手携帯会社名,
# 送受信主体者生年月日,出身地,出身地（国）,性別,送受信主体者携帯会社名,送信／受信,相手携帯会社名,相手ＩＤ,相手生年月日,相手出身地,相手出身地（国）,相手性別,相手親密度
# 「送信者携帯会社名（新設）」「受信者携帯会社名（新設）」「送信者生年月日」「受信者生年月日」

"""

次の列を持つDataFrameがあります．
年度,通しＮｏ．,送受信主体者生年月日,出身地,出身地（国）,性別,送受信主体者携帯会社名,送信／受信,相手携帯会社名,相手ＩＤ,相手生年月日,相手出身地,相手出身地（国）,相手性別,相手親密度,内／外,送受信年月日,送受信時刻,


このDataFrameに
新しく，
「sender_携帯会社名	sender_生年月日	sender_出身地	sender_出身地（国）	sender_性別	    receiver_携帯会社名	receiver_生年月日	receiver_出身地	receiver_出身地（国）	receiver_性別」
という10個の列を作ります．

このとき，各行において，
「送信／受信」列の値が「←」である場合は，
「相手携帯会社名	相手生年月日	相手出身地	相手出身地（国）	相手性別」
という5つの列の値を
「sender_携帯会社名	sender_生年月日	sender_出身地	sender_出身地（国）	sender_性別	」
に，
「送受信主体者携帯会社名	送受信主体者生年月日	出身地	出身地（国）	性別	」
という5つの列の値を
「receiver_携帯会社名	receiver_生年月日	receiver_出身地	receiver_出身地（国）	receiver_性別」
に入れてください．
また，「送信／受信」列の値が「←」である場合は，
「送受信主体者携帯会社名	送受信主体者生年月日	出身地	出身地（国）	性別	」
を
「sender_携帯会社名	sender_生年月日	sender_出身地	sender_出身地（国）	sender_性別	」
に，
「相手携帯会社名	相手生年月日	相手出身地	相手出身地（国）	相手性別」
を
「receiver_携帯会社名	receiver_生年月日	receiver_出身地	receiver_出身地（国）	receiver_性別」
に入れてください，



「	相手親密度」

"""

# 送信者：送受信主体者生年月日,出身地,出身地（国）,性別,送受信主体者携帯会社名
# 


# 年度,通しＮｏ．,送受信主体者生年月日,出身地,出身地（国）,性別,送受信主体者携帯会社名,送信／受信,相手携帯会社名,相手ＩＤ,相手生年月日,相手出身地,相手出身地（国）,相手性別,相手親密度,内／外,送受信年月日,送受信時刻,管理ＩＤ／題名／本文,本文,unicode参照１,unicode参照２,unicode参照３,unicode参照４,unicode参照５,unicode参照６,unicode参照７,unicode参照８,unicode参照９,unicode参照１０,unicode参照１１,unicode参照１２,unicode参照１３,unicode参照１４,unicode参照１５,unicode参照１６,unicode参照１７,unicode参照１８,unicode参照１９,unicode参照２０,unicode参照２１,unicode参照２２,unicode参照２３,unicode参照２４,unicode参照２５,unicode参照２６,unicode参照２７,unicode参照２８,unicode参照２９,unicode参照３０,unicode参照３１,unicode参照３２,unicode参照３３,unicode参照３４,unicode参照３５,unicode参照３６,unicode参照３７,unicode参照３８,unicode参照３９,unicode参照４０,unicode参照４１,unicode参照４２,unicode参照４３,unicode参照４４,unicode参照４５,unicode参照４６,unicode参照４７,unicode参照４８,unicode参照４９,unicode参照５０,unicode参照５１,unicode参照５２,unicode参照５３,unicode参照５４,unicode参照５５,unicode参照５６,unicode参照５７,unicode参照５８,unicode参照５９,unicode参照６０,unicode参照６１,unicode参照６２,unicode参照６３,unicode参照６４,unicode参照６５,unicode参照６６,unicode参照６７,unicode参照６８,unicode参照６９,unicode参照７０,unicode参照７１,unicode参照７２,unicode参照７３,unicode参照７４,unicode参照７５,unicode参照７６,unicode参照７７,unicode参照７８,unicode参照７９,unicode参照８０,unicode参照８１,unicode参照８２,unicode参照８３,unicode参照８４,unicode参照８５,unicode参照８６,unicode参照８７,unicode参照８８,unicode参照８９,unicode参照９０,unicode参照９１,unicode参照９２,unicode参照９３,unicode参照９４,unicode参照９５,unicode参照９６

"""

年度,通しＮｏ．,送受信主体者生年月日,出身地,出身地（国）,性別,送受信主体者携帯会社名,送信／受信,相手携帯会社名,相手ＩＤ,相手生年月日,相手出身地,相手出身地（国）,相手性別,相手親密度,内／外,送受信年月日,送受信時刻,管理ＩＤ／題名／本文,本文,unicode参照１,unicode参照２,unicode参照３,unicode参照４,unicode参照５,unicode参照６,unicode参照７,unicode参照８,unicode参照９,unicode参照１０,unicode参照１１,unicode参照１２,unicode参照１３,unicode参照１４,unicode参照１５,unicode参照１６,unicode参照１７,unicode参照１８,unicode参照１９,unicode参照２０,unicode参照２１,unicode参照２２,unicode参照２３,unicode参照２４,unicode参照２５,unicode参照２６,unicode参照２７,unicode参照２８,unicode参照２９,unicode参照３０,unicode参照３１,unicode参照３２,unicode参照３３,unicode参照３４,unicode参照３５,unicode参照３６,unicode参照３７,unicode参照３８,unicode参照３９,unicode参照４０,unicode参照４１,unicode参照４２,unicode参照４３,unicode参照４４,unicode参照４５,unicode参照４６,unicode参照４７,unicode参照４８,unicode参照４９,unicode参照５０,unicode参照５１,unicode参照５２,unicode参照５３,unicode参照５４,unicode参照５５,unicode参照５６,unicode参照５７,unicode参照５８,unicode参照５９,unicode参照６０,unicode参照６１,unicode参照６２,unicode参照６３,unicode参照６４,unicode参照６５,unicode参照６６,unicode参照６７,unicode参照６８,unicode参照６９,unicode参照７０,unicode参照７１,unicode参照７２,unicode参照７３,unicode参照７４,unicode参照７５,unicode参照７６,unicode参照７７,unicode参照７８,unicode参照７９,unicode参照８０,unicode参照８１,unicode参照８２,unicode参照８３,unicode参照８４,unicode参照８５,unicode参照８６,unicode参照８７,unicode参照８８,unicode参照８９,unicode参照９０,unicode参照９１,unicode参照９２,unicode参照９３,unicode参照９４,unicode参照９５,unicode参照９６
2005,50000010,19830627,茨城,国内,男,Ｖ,←,Ｖ,02CK0001,1982,茨城,国内,男,３,外,20010301,1256,管理ＩＤ,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
2005,50000020,19830627,茨城,国内,男,Ｖ,←,Ｖ,02CK0001,1982,茨城,国内,男,３,外,20010301,1256,題名,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
2005,50000030,19830627,茨城,国内,男,Ｖ,←,Ｖ,02CK0001,1982,茨城,国内,男,３,外,20010301,1256,本文,ありがとよー！,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
2005,50000040,19830627,茨城,国内,男,Ｖ,←,Ｖ,02CK0001,1982,茨城,国内,男,３,外,20010301,1256,本文,そのうち部活に顔出すからねー,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,


"""


def save_sr_info(input_filepath, output_filepath):

    df = pd.read_csv(input_filepath, dtype=str, keep_default_na=False)

    # 管理ＩＤの行だけ残す（アノテーションなかったらどうしよう）
    df = df[df['管理ＩＤ／題名／本文'] == '管理ＩＤ']
    df.drop_duplicates(subset=['通しＮｏ．', '年度'], inplace=True)

    # senderの列を作成
    df['sender_携帯会社名'] = df.apply(lambda row: row['相手携帯会社名'] if row['送信／受信'] == '←' else row['送受信主体者携帯会社名'], axis=1)
    df['sender_生年月日'] = df.apply(lambda row: row['相手生年月日'] if row['送信／受信'] == '←' else row['送受信主体者生年月日'], axis=1)
    df['sender_出身地'] = df.apply(lambda row: row['相手出身地'] if row['送信／受信'] == '←' else row['出身地'], axis=1)
    df['sender_出身地（国）'] = df.apply(lambda row: row['相手出身地（国）'] if row['送信／受信'] == '←' else row['出身地（国）'], axis=1)
    df['sender_性別'] = df.apply(lambda row: row['相手性別'] if row['送信／受信'] == '←' else row['性別'], axis=1)

    # receiverの列を作成
    df['receiver_携帯会社名'] = df.apply(lambda row: row['送受信主体者携帯会社名'] if row['送信／受信'] == '←' else row['相手携帯会社名'], axis=1)
    df['receiver_生年月日'] = df.apply(lambda row: row['送受信主体者生年月日'] if row['送信／受信'] == '←' else row['相手生年月日'], axis=1)
    df['receiver_出身地'] = df.apply(lambda row: row['出身地'] if row['送信／受信'] == '←' else row['相手出身地'], axis=1)
    df['receiver_出身地（国）'] = df.apply(lambda row: row['出身地（国）'] if row['送信／受信'] == '←' else row['相手出身地（国）'], axis=1)
    df['receiver_性別'] = df.apply(lambda row: row['性別'] if row['送信／受信'] == '←' else row['相手性別'], axis=1)

    columns_to_save = ['年度', '通しＮｏ．', '送信／受信', '送受信主体者携帯会社名', '相手親密度', '内／外']
    columns_to_save = columns_to_save + ['相手ＩＤ', '送受信年月日', '送受信時刻', ]

    columns_to_save = columns_to_save + ['sender_携帯会社名', 'sender_生年月日', 'sender_出身地', 'sender_出身地（国）', 'sender_性別', 
                        'receiver_携帯会社名', 'receiver_生年月日', 'receiver_出身地', 'receiver_出身地（国）', 'receiver_性別']

    df = df[columns_to_save]

    df.to_csv(output_filepath)

    return True



if __name__ == '__main__':

    # year_int = 2010
    # year_str = str(year_int)

    for i in range(2004,2011):
        year_int = i
        year_str = str(year_int)
        print("aaa")
        print(year_str)
        save_sr_info(input_filepath = year_str + '版.csv', output_filepath='sr_info_' + year_str + '.csv')



