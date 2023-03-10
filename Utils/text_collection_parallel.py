import pandas as pd
import json
import requests
from warcio import ArchiveIterator
import smart_open
import os 
import numpy as np 
from multiprocessing import set_start_method
from multiprocessing import get_context
from multiprocessing import pool 
import multiprocessing
from requests.adapters import HTTPAdapter
from requests.packages import urllib3
from requests.packages.urllib3.util.retry import Retry

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

df = pd.read_pickle('/Users/gocchini/Desktop/CC project/tutorial_following/results01-02.pkl')

trial_df = df[0:100]
trial_df['needed_warc'] = trial_df['needed_warc'].str.replace('/warc/', '/wet/').replace('warc.gz', 'warc.wet.gz') 


def text_getter(wet_file, url):
    r = requests.get(wet_file, stream = True)
    # print('got it')
    for record in ArchiveIterator(r.raw):        
        if record.rec_headers.get_header('WARC-Target-URI') == url:
            if record.rec_type == 'conversion':
                # with raw_stream it does not work, I get error 'LimitReader' object is not callable
                text = record.content_stream().read() 
                text = text.decode('utf-8')
                # print('done')
                return text
    # no text is found so raise error
    raise ValueError("text not found")


def lambda_getter(df): 
    df['text'] = df.apply(lambda x: text_getter(x['needed_warc'], x['url']), axis = 1)
    return df

#if you want to avoid the lambda function (not that I would)

def text_getter_non_lambda(df):
    session = requests.Session()
    retryer = Retry(
        total=5, read=5, connect=5, backoff_factor=0.2, status=1, redirect=1, status_forcelist=None)
    for index in df.index:
        wet_file = df.loc[index, 'needed_warc']
        url = df.loc[index, 'url']
        print(url)
        r = session.get(wet_file, stream = True)
        print('got it')
        for record in ArchiveIterator(r.raw):
            if record.rec_headers.get_header('WARC-Target-URI') == url:
                if record.rec_type == 'conversion':
                    # with raw_stream it does not work, I get error 'LimitReader' object is not callable
                    text = record.content_stream().read() 
                    text = text.decode('utf-8')
                    df.loc[index,'text'] = text
                    # need to add some break statements around here
    session.close()
    print('completed chunk')
    return df


def parallelize_df(df, function):
    n_cores = os.cpu_count()
    df_split = np.array_split(df, n_cores)
    with get_context('fork').Pool(processes = n_cores) as pool:
        df = pd.concat(pool.map(function, df_split))
        pool.close()
        pool.join()
    return df

if __name__ == '__main__':

    #set_start_method("fork")
    #res = text_getter_parallel(trial_df)
    res = parallelize_df(trial_df, lambda_getter)
    print(res)
