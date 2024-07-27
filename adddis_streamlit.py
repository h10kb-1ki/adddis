import streamlit as st
import pandas as pd
import datetime
import altair as alt

st.title('AddDisデータ分析')
st.write('')

# データの読込み-----------------------------------------------
df = pd.read_excel('AddDis調製データ.xlsx')

# 時間ごとの調製件数（1日）-----------------------------
dates = sorted(list(set(df['実施日'].tolist())))
#dates = df['実施日'].unique().tolist()  #これだと上手くdatetimeにならない
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
drugs = sorted(df4['stem'].unique().tolist())
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

# ヒストグラムと平均調製時間-----------------------------
with st.sidebar:
    st.write('---')
    std_drug = st.selectbox('標準薬', ['GEM', 'Aza', 'PTX'])
    ph = st.selectbox('調製者', sorted(df['調製者'].unique().tolist()))
    btn4 = st.button('平均調製時間')
if btn4:
    df_hist = df4.query(f'stem == "{std_drug}"')
    df_hist = df_hist[['調製者', 'mg', 'prep_time']]
    df_hist_ph = df_hist.query(f'調製者 == "{ph}"')
    df_hist_ph.rename(columns={'prep_time': '調製時間'}, inplace=True)
    if len(df_hist_ph) == 0:
        st.write(f'{ph}の{std_drug}調製歴はありません。')
    else:
        mean = df_hist_ph['調製時間'].mean()
        base = alt.Chart(df_hist).mark_bar().encode(
                x=alt.X('prep_time:Q', 
                        bin=alt.Bin(maxbins=20),
                        title='調製時間(min)'
                        ),
                y=alt.Y('count()', title='')
                ).properties(
                title=f'{std_drug}調製時間の分布と平均値({ph})')
        rule = base.mark_rule(
                    size=1, color='red'
                    ).encode(x=alt.datum(mean))
        st.altair_chart(base + rule)
        st.write(f'平均調製時間: {mean:.1f}(min)')
        st.dataframe(df_hist_ph)