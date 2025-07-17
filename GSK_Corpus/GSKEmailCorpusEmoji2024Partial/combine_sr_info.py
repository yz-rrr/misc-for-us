import pandas as pd

# List to store DataFrames of each CSV file
dfs = []

# Loop through the CSV files and read them into DataFrames
for year in range(2004, 2011):
    filename = f"sr_info_{year}.csv"
    df = pd.read_csv(filename, dtype="str")
    dfs.append(df)
    print(len(df))

# Concatenate all DataFrames into a single DataFrame
combined_df = pd.concat(dfs, ignore_index=True)
combined_df = combined_df.drop_duplicates(subset=['通しＮｏ．', '年度'])

print(len(combined_df))

# Display the combined DataFrame
combined_df.to_csv("sr_info_2004-2010.csv")