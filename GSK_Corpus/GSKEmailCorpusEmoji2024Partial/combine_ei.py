import pandas as pd

# List to store DataFrames of each CSV file
dfs = []

# Loop through the CSV files and read them into DataFrames
for year in range(2004, 2011):
    filename = f"ed_ei{year}.csv"
    df = pd.read_csv(filename, dtype={"emoji_list": object, "position_list": object, "年度": str, "通しＮｏ．": str})
    dfs.append(df)
    print(len(df))

# Concatenate all DataFrames into a single DataFrame
combined_df = pd.concat(dfs, ignore_index=True)
print(len(combined_df))

# Display the combined DataFrame
combined_df.to_csv("ed_ei_2004-2010.csv")

df_drdu = combined_df.drop_duplicates(subset=['年度', '通しＮｏ．'], keep='last')

# df_drdu.to_csv("ed_ei_2004-2010_0509重複削除.csv")
df_drdu.to_csv("ed_ei_2004-2010_0625重複削除.csv")
