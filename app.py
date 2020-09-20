# covid-hk is a simple and clean web app
# to display the covid HK numbers from the HK government data
# The data is refreshed daily
# This version v0.5
# Daniel Lewis September 2020

import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
import datetime
from pathlib import Path
import base64
import requests
import io

st.beta_set_page_config(
    page_title='covid-hk',
    #page_icon='',
    #layout='wide',
    #initial_sidebar_state='expanded'
)

def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

def header():
    hide_streamlit_style = '''
<style>
MainMenu {visibility:hidden;}
footer {visibility:hidden;}
</style>
    '''
    #st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    header_html = "<img src='data:image/png;base64,{}' class='img-fluid'>".format(
        img_to_bytes('header.png')
    )
    st.markdown(header_html, unsafe_allow_html=True)

    return None

#@st.cache
def get_data():

    cbc_url = 'http://www.chp.gov.hk/files/misc/enhanced_sur_covid_19_eng.csv'

    cbc_data = requests.get(cbc_url).content
    cbc = pd.read_csv(io.StringIO(cbc_data.decode('utf-8')),
                      usecols=['Case no.', 'Report date', 'Date of onset',
                               'Gender', 'Age', 'HK/Non-HK resident',
                               'Case classification*']
                     ).fillna(0)

    cbc.rename(columns = {'Case no.':'case_num',
                          'Report date':'report_date',
                          'Date of onset':'onset_date',
                          'Gender':'sex',
                          'Age':'age',
                          'HK/Non-HK resident':'resident',
                          'Case classification*':'type'}, inplace=True)

    cbc['type'] = cbc['type'].str.replace('Epidemiologically linked', 'Linked', case=True)
    cbc['type'] = cbc['type'].str.replace('Linked with possibly l', 'Linked with l', case=True)
    cbc['type'] = cbc['type'].str.replace('Possibly l', 'L', case=True)

    cbc['type'] = cbc['type'].str.replace('Imported', '1. Imported', case=True)
    cbc['type'] = cbc['type'].str.replace('Linked with i', '2. Linked with i', case=True)
    cbc['type'] = cbc['type'].str.replace('Local', '3. Local', case=True)
    cbc['type'] = cbc['type'].str.replace('Linked with l', '4. Linked with l', case=True)

    cbc.set_index('case_num', inplace=True)
    cbc['report_date'] = pd.to_datetime(cbc['report_date'], dayfirst=True)
    cbc['report_date_d'] = cbc['report_date'].dt.date

    #cum = pd.read_csv(,
    cum_url = 'http://www.chp.gov.hk/files/misc/latest_situation_of_reported_cases_covid_19_eng.csv'

    cum_data = requests.get(cum_url).content
    cum = pd.read_csv(io.StringIO(cum_data.decode('utf-8')),
                      usecols=['As of date',
                               'Number of confirmed cases',
                               'Number of death cases']).fillna(0)
    cum.rename(columns = {'As of date':'date',
             'Number of confirmed cases':'total_cases',
             'Number of death cases':'total_deaths'}, inplace=True)
    cum['date'] = pd.to_datetime(cum['date'], dayfirst=True)

    case_list = cum.total_cases.tolist()
    deaths_list = cum.total_deaths.tolist()
    day_case_list = [0]
    day_death_list = [0]
    for idx in range(1, len(case_list)):
        day_case_list.append(case_list[idx]-case_list[idx-1])
        day_death_list.append(deaths_list[idx]-deaths_list[idx-1])

    cum['day_cases'] = day_case_list
    cum['day_deaths'] = day_death_list

    return cbc, cum

def footer():
    st.markdown('---')
    st.markdown('''NB cases reported for a specific date are the cases announced on that date, as of 00:00, and so represent cases in the preceding 24 hours''')
    st.markdown('---')
    st.markdown('''<img src='data:image/png;base64,{}' class='img-fluid' width=32 height=32>'''.format(img_to_bytes("brain.png")), unsafe_allow_html=True)
    st.markdown('''<small>covid-hk | Mk 5 | September 2020 | [https://github.com/daniellewisDL/covid-hk](https://github.com/daniellewisDL/covid-hk) | Data source files: [data.gov.hk](https://data.gov.hk/en-data/dataset/hk-dh-chpsebcddr-novel-infectious-agent)</small>
                ''', unsafe_allow_html=True)

    return None

def main():

    header()

    st.markdown('---')

    case_by_case_data, cumulative_data = get_data()

    recent_case_nums = cumulative_data.tail(5).iloc[::-1]['day_cases'].tolist()
    recent_case_dates = cumulative_data.tail(5).iloc[::-1]['date'].tolist()

    hdr = recent_case_dates[0].strftime('%a %d %b %Y')

    st.subheader(hdr)
    st.markdown('''<span style='color: #f63366; font-size: 50pt;'>{}<b style='color: black; font-size: 20pt;'>cases</b></span>'''.format(recent_case_nums[0]), unsafe_allow_html=True)
    st.markdown('''<span style='color: black; font-size: 10pt;'><b>{} </b>({}) | <b>{} </b>({}) | <b>{} </b>({}) | <b>{} </b>({})</span>'''.format(
                    recent_case_nums[1], recent_case_dates[1].strftime('%d %b'),
                    recent_case_nums[2], recent_case_dates[2].strftime('%d %b'),
                    recent_case_nums[3], recent_case_dates[3].strftime('%d %b'),
                    recent_case_nums[4], recent_case_dates[4].strftime('%d %b')
                    ), unsafe_allow_html=True)

    st.markdown('''Breakdown of the {} cases on {}:'''.format(recent_case_nums[0], hdr))
    st.write(case_by_case_data[case_by_case_data['report_date_d']==recent_case_dates[0]].type.value_counts())

    if st.checkbox('More details on these ', value=False):
        st.table(case_by_case_data[case_by_case_data['report_date_d']==recent_case_dates[0]].drop(['report_date', 'report_date_d'], axis=1))
        st.subheader('Full table of cumulative and daily cases and deaths')
        st.dataframe(cumulative_data.iloc[::-1])
        st.markdown('---')
    if st.checkbox('Charts and more details', value=False):
        st.subheader('Summary charts')

        row_count = cumulative_data.shape[0]
        day_count = st.slider('Most recent x days', 1, row_count, 90)
        day_chart_df = cumulative_data.drop(['total_cases', 'total_deaths', 'day_deaths'], axis=1).iloc[row_count-day_count:]
        day_cases_chart = alt.Chart(day_chart_df, title = 'Daily cases').mark_bar().encode(
                        x=alt.X('date', axis=alt.Axis(format='%Y-%m-%d', title='Date', labelAngle=-90)),
                        y=alt.Y('day_cases', axis=alt.Axis(title='Cases')),
                        tooltip = [alt.Tooltip(field='date', type='temporal', format='%Y-%m-%d'),
                                   alt.Tooltip(field='day_cases', title='cases', type='quantitative', format=',')]
                        ).interactive()
        st.altair_chart(day_cases_chart, use_container_width=True)

        grouped_type_df = case_by_case_data.groupby(['report_date_d', 'type'], as_index=False)['age'].count()
        grouped_type_df.rename(columns={'report_date_d':'date', 'age':'num'}, inplace=True)
        grouped_chart = alt.Chart(grouped_type_df, title='Daily cases by type').mark_bar().encode(
                        x=alt.X('date', axis=alt.Axis(format='%Y-%m-%d', title='Date', labelAngle=-90)),
                        y=alt.Y('num', axis=alt.Axis(title='Cases')),
                        color='type:N',
                        tooltip = [alt.Tooltip(field='date', type='temporal', format='%Y-%m-%d'),
                                   alt.Tooltip(field='type', type='nominal'),
                                   alt.Tooltip(field='num', title='cases', type='quantitative', format=',')]
                        ).interactive()
        st.altair_chart(grouped_chart, use_container_width=True)

        step = 50
        overlap = 1.1
        type_counts_chart = alt.Chart(grouped_type_df, height=step
                ).transform_joinaggregate(
                    cases='sum(num)', groupby=['type']
                ).mark_area(
                ).encode(
                    x=alt.X('date', axis=alt.Axis(format='%Y-%m-%d', title='Date', labelAngle=-90)),
                    y=alt.Y('num:Q', axis=None),
                ).facet(
                    row=alt.Row(
                        'type:N',
                        title=None,
                        header=alt.Header(labelAngle=0, labelAlign='left')
                    )
                ).properties(
                    title='Cases by type',
                ).configure_facet(
                    spacing=-200
                ).configure_view(
                    stroke=None
                ).configure_title(
                    anchor='end'
                )
        st.altair_chart(type_counts_chart, use_container_width=True)


        st.markdown('---')
        st.subheader('Get more info on a specific date')
        dt = st.date_input('Choose specific date', value=recent_case_dates[0])
        dt_df = case_by_case_data[case_by_case_data['report_date_d']==dt]
        st.text(dt.strftime('%a %d %b %Y'))
        st.markdown('''<span style='color: #f63366; font-size: 50pt;'>{}<b style='color: black; font-size: 20pt;'>cases</b></span>'''.format(dt_df.shape[0]), unsafe_allow_html=True)
        st.text('Of which:')
        st.write(dt_df.type.value_counts())
        st.write(dt_df)



    footer()

    return None

if __name__ == '__main__':
    main()
