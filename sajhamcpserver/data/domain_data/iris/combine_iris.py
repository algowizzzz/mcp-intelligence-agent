import os, glob
import pandas as pd

def combine():
    base = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(base, 'IRIS_ALL_PROD_UTIL_*.csv')
    frames = []
    for f in sorted(glob.glob(pattern)):
        date = os.path.basename(f).replace('IRIS_ALL_PROD_UTIL_','').replace('.csv','')
        df = pd.read_csv(f, encoding='latin1', low_memory=False)
        df.insert(0, 'Date', date)
        frames.append(df)
    if frames:
        out = pd.concat(frames, ignore_index=True)
        out.to_csv(os.path.join(base, 'iris_combined.csv'), index=False, encoding='latin1')
        print(f'Written {len(out)} rows to iris_combined.csv')

if __name__ == '__main__':
    combine()
