import csv
import json
import os
import re
import numpy as np
import pandas as pd


# これでデータを吐けばあとの解析は前のプログラム適用できるのではないか（したほうが安全か）

# 絵文字抽出系：make_emoji_pos_rough.py -> combine_ei.py（結合して重複削除）（srは別の流れ make_mo-MC_mails.py）


HW_target = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789%()'
FW_target = 'ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ０１２３４５６７８９％（）'
H2F_target = str.maketrans(HW_target, FW_target)


def culc_emoji_pos_in_body(body):

    total_emoji_list = []
    total_position_list = []

    empty_flag = False

    if body is None:
        empty_flag = True 
    elif body == "":
        empty_flag = True 

    if empty_flag:
        return {'emoji_list': [], 'position_list': []}

    body = str(body)
    lines = body.split("\n")

    for line in lines:
        info = culc_emoji_pos_in_line(line.strip())
        total_emoji_list = total_emoji_list + info['emoji_list']
        total_position_list = total_position_list + info['position_list']

    return {'emoji_list': total_emoji_list, 'position_list': total_position_list}


def culc_emoji_pos_in_title(title):

    total_emoji_list = []
    total_position_list = []

    empty_flag = False

    if title is None:
        empty_flag = True 
    elif title == "":
        empty_flag = True 

    if empty_flag:
        return {'emoji_list': [], 'position_list': []}

    title = str(title)
    lines = title.split("\n")

    for line in lines:
        info = culc_emoji_pos_in_line(line.strip())
        total_emoji_list = total_emoji_list + info['emoji_list']
        total_position_list = total_position_list + info['position_list']

    return {'emoji_list': total_emoji_list, 'position_list': total_position_list}



"""

4/24

3〜4歳：一部スロットに
「面白い表現」

"abstraction"と"generalization" ニュアンスとしてはabstractionのほうが抽出する的なのがあるかもだがやってることは同じでいいと

・認知文法パート
際立ちの話
字面そのまま際立ちだというわけではない
述語の意味　関係として見ている（関係的）　「動詞に際立ちを与えるのは難しいだろう」という考え方
・名詞　participants, setting（セッティング　場所的なのとか） / 動詞　relation（participants間の）
・QA「SVOO - I gave Mary it. ができない - 焦点をあてたいものを後に持ってくる（と習った）」との両立について：
　文末焦点：文末もそれなりに目立つポジション　（ただし実際に Give me itが全くないわけではなかった(特にBNCというイギリス英語の方がCOCAより比率がなだらか)(Goldberg 2019)）

5/8 "Raising and Transparency" (Langacker 1995) - 3週間程度
Goldberg "Surface Generalization: An Alternative to Alternation" - 3週間程度？
そのあとは言語獲得テーマを許す限りとのこと

"""



def extract_emojinames(lst):
    emojinames = []
    for elem in lst:
        x = elem.strip()
        x = x.translate(H2F_target)
        x = x.replace('％％絵（', '').replace('）％％', '')
        # 困ったことに同じ記号が1個だけあった　ミス？
        emojinames.append(x)
    return emojinames

def culc_emoji_pos_in_line(line):

    # 5/3: re.compile("％％絵(（.+?）)％％")で取っていたが，わずかに％％絵()％％があり
    pattern = re.compile("％％絵(（.*?）)％％")
    # pattern_s = re.compile("^％％絵(（.+?）)％％")
    # pattern_e = re.compile("％％絵(（.+?）)％％$")

    # 6/25：半角表記揺れに対応。半角が全部全角になってしまうのが残念ではあるが。
    line = line.strip().translate(H2F_target)

    # print(line)
    line_len = len(line)

    start_flag = False
    end_flag = False

    # target_s = line

    position_list = []

    span_list = []
    emoji_list = []

    # all_flag = False

    all = pattern.findall(line)
    # print(all)
    all_iter = pattern.finditer(line)

    for m in all_iter:
        span_list.append({'start': m.start(), 'end': m.end()})
        emoji_list.append(m.group())
    
    now_s_end = None
    now_e_start = None
    s_block_edge_index = None
    e_block_edge_index = None
    start_counter = 0
    end_counter = 0

    if len(span_list) == 0:
        return {'emoji_list': [], 'position_list': []}

    if span_list[0]['start'] == 0:
        start_flag = True
        now_s_end = span_list[0]['end']
        s_block_edge_index = 0
        start_counter = 1
    if span_list[-1]['end'] == line_len:
        # print(span_list[-1]['end'])
        end_flag = True
        now_e_start = span_list[-1]['start']
        e_block_edge_index = 1
        end_counter = 1
    
    # print(start_flag)
    # print(end_flag)
    
    while start_flag:
        if len(span_list) > s_block_edge_index + 1:
            if now_s_end == span_list[s_block_edge_index + 1]['start']:
                start_flag = True
                s_block_edge_index = s_block_edge_index + 1
                now_s_end = span_list[s_block_edge_index]['end']
                start_counter = start_counter + 1
            else:
                start_flag = False
        else:
            break
        
    while end_flag:
        # endだとindexが1つ増えていることに注意
        if len(span_list) >= e_block_edge_index + 1:
            # print(end_counter)
            if now_e_start == span_list[-(e_block_edge_index+1)]['end']:
                end_flag = True
                e_block_edge_index = e_block_edge_index + 1
                now_e_start = span_list[-e_block_edge_index]['start']
                end_counter = end_counter + 1
            else:
                end_flag = False
        else:
            break
        
    # print(now_s_end)
    # print(now_e_start)

    # print("counter: " + str(start_counter) + " - " + str(end_counter))


    if (start_flag) and (end_flag):
        if len(emoji_list) <= 1:
            position_list = ['wt' for i in range(len(emoji_list))]
        else:
            position_list = ['wf'] + ['wm' for i in range(len(emoji_list) - 2)] + ['wl']
    else:
        position_list = []
        if start_counter >= 1:
            position_list = position_list + ['f0']
            position_list = position_list + ['f1' for i in range(start_counter - 1)]
        position_list = position_list + ['m0' for i in range(len(emoji_list) - start_counter - end_counter)]
        if end_counter >= 1:
            position_list = position_list + ['l1' for i in range(end_counter - 1)]
            position_list = position_list + ['l0']


    # print(position_list)


    # spanで処理する手もあるよなあ　元々そうしたみたいに
    

    """
    while line_start_with_emoji == True:

        m = pattern_s.search(target_s)
        if m is None:
            line_start_with_emoji = False
        else:
            hit = m.group(0)
            print("hit: " + hit)
            target_s = target_s[m.end():]
            print("nokori: " + target_s)
            start_hits.append(hit)

        if len(target_s) == 0:
            all_flag = True

    """

    return {'emoji_list': emoji_list, 'position_list': position_list}



def test_1():

    line1 = "明日は頑張ろうね％％絵（Ｅ６Ｆ０）％％％％絵（Ｅ６９４）％％％％絵（Ｅ６９６）％％"
    line2 = "％％絵（Ｅ７０４）％％％％絵（Ｅ７０５）％％あああ"
    line3 = "％％絵（Ｅ７０４）％％％％絵（Ｅ７０５）％％"
    line4 = "％％絵（Ｅ７０４）％％おおお％％絵（Ｅ７０５）％％"
    line5 = "おおお％％絵（Ｅ７０４）％％おおお％％絵（Ｅ７０５）％％おおお"
    line6 = "％％絵（Ｅ７０４）％％％％絵（Ｅ７０５）％％％％絵（Ｅ７０５）％％"
    line7 = "％％絵（Ｅ７０４）％％"


    print("末尾3つ")
    res = culc_emoji_pos_in_line(line1)
    print(res)
    print("先頭2つ")
    res = culc_emoji_pos_in_line(line2)
    print(res)
    print("全体2つ")
    culc_emoji_pos_in_line(line3)
    print("先頭1つと末尾1つ")
    culc_emoji_pos_in_line(line4)
    print("中間にばらばらに2つ")
    culc_emoji_pos_in_line(line5)
    print("全体3つ")
    culc_emoji_pos_in_line(line6)
    print("全体1つ")
    culc_emoji_pos_in_line(line7)

    return True



def test_2():

    body1 = """明日は頑張ろうね％％絵（Ｅ６Ｆ０）％％％％絵（Ｅ６９４）％％％％絵（Ｅ６９６）％％
    ％％絵（Ｅ７０４）％％％％絵（Ｅ７０５）％％あああ"""
    body2 = "％％絵（Ｅ７０４）％％％％絵（Ｅ７０５）％％\n％％絵（Ｅ７０４）％％おおお％％絵（Ｅ７０５）％％"
    body3 = "おおお％％絵（Ｅ７０４）％％おおお％％絵（Ｅ７０５）％％おおお\n％％絵（Ｅ７０４）％％％％絵（Ｅ７０５）％％％％絵（Ｅ７０５）％％\n％％絵（Ｅ７０４）％％"


    print("末尾3つ")
    print("先頭2つ")
    res = culc_emoji_pos_in_body(body1)
    print(res)
    print("全体2つ")
    print("先頭1つと末尾1つ")
    res = culc_emoji_pos_in_body(body2)
    print(res)
    print("中間にばらばらに2つ")
    print("全体3つ")
    print("全体1つ")
    res = culc_emoji_pos_in_body(body3)
    print(res)
    return True


def get_emoji_list(x):
    return x['emoji_list']

def get_position_list(x):
    return x['position_list']


def emoji_info_to_csv(df, filename, save_columns_mode="limited"):

    # df['emoji_position'] = df['body_combined'].apply(lambda x: )

    emoji_list_list = []
    position_list_list = []

    df['emoji_position_in_body'] = df['body_combined'].apply(culc_emoji_pos_in_body)
    df['emoji_position_in_title'] = df['title'].apply(culc_emoji_pos_in_body)

    df['emoji_list_body'] = df['emoji_position_in_body'].apply(get_emoji_list)
    df['position_list_body'] = df['emoji_position_in_body'].apply(get_position_list)

    df['emoji_list_title'] = df['emoji_position_in_title'].apply(get_emoji_list)
    df['position_list_title'] = df['emoji_position_in_title'].apply(get_position_list)


    """
    for index, row in df.iterrows():

        emoji_position_info = culc_emoji_pos_in_body(row['body_combined'])
        emoji_list_list.append(emoji_position_info['emoji_list'])
        position_list_list.append(emoji_position_info['position_list'])

    df['emoji_list'] = pd.Series(emoji_list_list)
    df['position_list'] = pd.Series(position_list_list)

    """
    
    df.drop('emoji_position_in_body', axis=1)
    df.drop('emoji_position_in_title', axis=1)

    print(df.head())

    if save_columns_mode == "all":
        df.to_csv(filename)
    elif save_columns_mode == "limited":
        df = df[['年度', '通しＮｏ．', 'title', 'body_combined', 
                'emoji_list_body', 'position_list_body', 
                'emoji_list_title', 'position_list_title']]
        df.to_csv(filename)

    return True


if __name__ == '__main__':

    for i in range(2004,2011):
        year_int = i
        year_str = str(year_int) 

        df = pd.read_csv('ed_' + year_str + '.csv', dtype=str)
        emoji_info_to_csv(df=df, filename='ed_ei' + year_str + '.csv')

    print("aaa")
    #    mail_items_to_csv(filename='ed_' + year_str + '.csv')

    # test_1()
    # test_2()

