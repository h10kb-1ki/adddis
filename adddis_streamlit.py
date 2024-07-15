import streamlit as st
import pandas as pd
import datetime
import altair as alt
#import numpy as np
#import matplotlib.pyplot as plt
#import seaborn as sns
#import japanize_matplotlib

st.title('Adddisデータ分析')
st.write('')

# データの整形-----------------------------------------------
df = df = pd.read_csv('AddDis調製データ.csv', encoding='cp932')
krebs = pd.read_excel('mst_data.xlsx', sheet_name='krebs')
ex = pd.read_excel('mst_data.xlsx', sheet_name='exclusion')
exclusion = ex['薬品コード'].to_list()
# str日付をdatetimeに変換
df['実施日'] = pd.to_datetime(df['実施日'])
for i in range(len(df)):
    dt = df.loc[i, '実施日']
    startTime = df.loc[i, '調製開始']
    startTime = f'{startTime:08}'  #0埋め
    h1 = int(startTime[0:2])
    m1 = int(startTime[3:5])
    s1= int(startTime[6:8])
    df.loc[i, '調製開始'] = dt + datetime.timedelta(hours=h1, minutes=m1, seconds=s1)

    m2 = int(df.loc[i, '調製時間'][2:4])
    s2= int(df.loc[i, '調製時間'][5:7])
    df.loc[i, '調製時間'] = dt + datetime.timedelta(minutes=m2, seconds=s2)

    if type(df.loc[i, '保留時間']) == float:  #csv 空欄はfloat
        df.loc[i, '保留時間'] = dt
    else:
        m3= int(df.loc[i, '保留時間'][2:4])
        s3= int(df.loc[i, '保留時間'][5:7])
        df.loc[i, '保留時間'] = dt + datetime.timedelta(minutes=m3, seconds=s3)
    
df1 = df.query('薬品コード != @exclusion')
df1 = df1[['実施日', '入外', '科名', '病棟', 'オーダー番号', '調製者', '薬品本数', '薬品コード', '薬品名', '調製開始', '調製時間', '保留時間',]]
df1.sort_values('オーダー番号', ascending=True, inplace=True)

#オーダ番号がないレコードは削除
df1.dropna(subset='オーダー番号', inplace=True)
df1 = pd.merge(df1, krebs, how='inner')
#df1.sort_values('オーダー番号', ascending=True, inplace=True)

#オーダー番号と用量（合計）の紐づけ
df1['mg'] = df1['薬品本数'] * df1['contain']

dose = df1.pivot_table(index='オーダー番号', values='mg', aggfunc='sum')
dose.reset_index(inplace=True)

# 調製時間の算出
prep_times = []
for i in range(len(df1)):
    tdelta = df1.loc[i, '調製時間'] - df1.loc[i, '保留時間']
    sec = tdelta.total_seconds()  #秒に換算
    prep_times.append(sec/60)
df1['prep_time'] = prep_times
df = df1[['実施日', '入外', '科名', '病棟', 'オーダー番号', '薬品本数', '薬品コード', '薬品名', '調製開始', 'stem', 'contain', 'prep_time', '調製者']]

df.drop_duplicates(subset='オーダー番号', keep='first', inplace=True)
df = pd.merge(df, dose, how='outer')

hours = []
for i in range(len(df)):
    hour = df.loc[i, '調製開始'].strftime('%H時')
    hours.append(hour)
df['hour'] = hours
dates = sorted(list(set(df['実施日'].tolist())))

# 時間ごとの調製件数（1日）-----------------------------
with st.sidebar:
    day = st.date_input('日を指定', dates[0], min_value=dates[0], max_value=dates[len(dates)-1])
    btn1 = st.button('時間ごとの調製件数（1日）')
    st.write('---')
ymd = day.strftime('%Y/%m/%d')
weekday = day.weekday()
wd_dic = {0: 'Mon', 
          1: 'Tue', 
          2: 'Wed', 
          3: 'Thu', 
          4: 'Fri', 
          5: 'Sat', 
          6: 'Sun'}
if btn1:
    df2 = df[['実施日', '入外', 'オーダー番号', 'hour']]
    df2m = pd.melt(df2, id_vars=['実施日', 'hour', '入外'])
    dfq = df2m.query(f'実施日 == "{day}"')
    bars = alt.Chart(dfq).mark_bar(size=25).encode(
                x=alt.X('hour', title='時間', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('count(value)', title='調製件数').stack('zero'),
                color=alt.Color('入外', scale=alt.Scale(domain=['入院', '外来'], range=['skyblue', 'dodgerblue'])),
                tooltip=[alt.Tooltip('hour', title='時間'), 
                        alt.Tooltip('入外', title='入外'),  
                        alt.Tooltip('count(value)', format='.0f', title='調製件数')
                        ]
                ).properties(
                    width=450,
                    height=350,
                    title=f'時間ごとの調製件数  {ymd} ({wd_dic[weekday]})'
                    )
    text = alt.Chart(dfq).mark_text(dx=0, dy=-5, color='black').encode(
                x=alt.X('hour'),
                y=alt.Y('count(value)').stack('zero'),
                detail='入外',
                text=alt.Text('count(value)', format='.0f')
                )
    st.altair_chart(bars + text, use_container_width=True)

    
# 時間ごとの調製件数（複数日）-----------------------------
with st.sidebar:
    start = st.date_input('開始日', dates[0], 
                        min_value=dates[0], max_value=dates[len(dates)-1])
    end = st.date_input('終了日', dates[len(dates)-1], 
                        min_value=start, max_value=dates[len(dates)-1])
    btn2 = st.button('時間ごとの調製件数（標準偏差）')
    st.write('---')
if btn2:
    dfq = df.query(f'"{start}" <= 実施日 <= "{end}"')
    df3 = dfq.pivot_table(index=['実施日', 'hour'], columns='入外', values='オーダー番号', aggfunc='count')
    df3.reset_index(inplace=True)
    df3 = pd.melt(df3, id_vars=['実施日', 'hour'], value_vars=['入院', '外来'], var_name='入外', value_name='count')
    start_ymd = start.strftime('%Y/%m/%d')
    end_ymd = end.strftime('%Y/%m/%d')
    line = alt.Chart(df3).mark_line().encode(
            x=alt.X('hour', title='時間', axis=alt.Axis(labelAngle=0)),
            y='mean(count)',
            color=alt.Color('入外', scale=alt.Scale(domain=['入院', '外来'], range=['skyblue', 'dodgerblue'])),
            tooltip=[alt.Tooltip('hour', title='時間'), 
                     alt.Tooltip('入外', title='入外'),
                     alt.Tooltip('mean(count)', format='.0f', title='調製件数')
                    ]).properties(
                        width=400,
                        height=300, 
                        title=f'時間ごとの調製件数 {start_ymd} ～ {end_ymd}'
                        )
    band = alt.Chart(df3).mark_errorband(extent='stdev').encode(
        x='hour',
        y=alt.Y('count', title='時間あたりの調製件数'),
        color='入外',
    )
    st.altair_chart(line + band, use_container_width=True)


# 医薬品ごとの調製時間-----------------------------
df4 = df.dropna(subset='stem') #マスタにない薬剤（Nan）を削除
#選択した薬剤の用量別調製時間を確認
drugs = df4['stem'].unique().tolist()
with st.sidebar:
    drug = st.selectbox('抗がん薬を選択', drugs)
    btn3 = st.button('調製時間の分布')

def create_jointplot(df4, drug):
    df4 = df4[['stem', '調製者', 'prep_time', 'mg']]
    df4q = df4.query(f'stem == "{drug}"')
    base = alt.Chart(df4q)
    base_bar = base.mark_bar(opacity=0.5, binSpacing=0)
    xscale = alt.Scale(domain=(df4q['prep_time'].min()*0.7, df4q['prep_time'].max()*1.1))
    yscale = alt.Scale(domain=(df4q['mg'].min()*0.7, df4q['mg'].max()*1.1))
    points = base.mark_circle().encode(
        alt.X('prep_time', title='調製時間(min)', scale=xscale),
        alt.Y('mg', title='用量', scale=yscale),
        tooltip=[
                '調製者', 
                alt.Tooltip('mg:Q', format='.1f', title='用量'), 
                alt.Tooltip('prep_time:Q', format='.2f', title='調製時間'), 
                ])
    top_hist = (base_bar.encode(
                    alt.X('prep_time:Q',
                        bin=alt.Bin(maxbins=20, extent=xscale.domain),
                        stack=None,
                        title="",),
                    alt.Y("count()", stack=None, title=""),
                    ).properties(height=60)
                )
    right_hist = (base_bar.encode(
                    alt.Y('mg:Q',
                        bin=alt.Bin(maxbins=20, extent=yscale.domain),
                        stack=None,
                        title="",),
                    alt.X("count()", stack=None, title=""),
                    ).properties(width=60)
                )
    #調製速度のランキングを作成
    df_rank = df4q.pivot_table(index='調製者', values='prep_time', aggfunc=['count', 'min', 'max', 'mean'])
    df_rank.columns = ['回数', 'min', 'max', '平均']
    df_rank.sort_values('平均', ascending=True, inplace=True)
    return points, top_hist, right_hist, df_rank.round(2)

if btn3:
    points, top_hist, right_hist, df_rank = create_jointplot(df4, drug)
    st.write(drug)
    st.altair_chart(top_hist & (points | right_hist))
    st.write('')
    st.dataframe(df_rank)
