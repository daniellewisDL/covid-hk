# covid-hk is a simple web app
# to display the covid HK case numbers and vaccination rates from the HK government data
# The data is refreshed daily

import streamlit as st
from st_radial import st_radial
from st_card import st_card
import streamlit_apex_charts
import numpy as np
import pandas as pd
import altair as alt
import datetime
from os import path
import base64
import requests
import io

st.set_page_config(
    page_title='covid-hk',
    #page_icon='',
    #layout='wide',
    #initial_sidebar_state='expanded'
)

# Thanks to GokulNC for this code snippet
@st.cache(allow_output_mutation=True)
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

@st.cache(allow_output_mutation=True)
def get_img_with_href(local_img_path, target_url):
    img_format = path.splitext(local_img_path)[-1].replace('.', '')
    bin_str = get_base64_of_bin_file(local_img_path)
    html_code = f'''
        <a href="{target_url}" target="_blank">
            <img src="data:image/{img_format};base64,{bin_str}" />
        </a>'''
    return html_code



#@st.cache
def get_data():

    cbc_url = 'http://www.chp.gov.hk/files/misc/enhanced_sur_covid_19_eng.csv'

    cbc_data = requests.get(cbc_url).content
    cbc = pd.read_csv(io.StringIO(cbc_data.decode('utf-8')),
                      usecols=['Case no.', 'Report date', 'Age',
                               'Case classification*']
                     ).fillna(0)

    cbc.rename(columns = {'Case no.':'case_num',
                          'Report date':'report_date',
                          'Age' : 'age',
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


    vac_url = 'https://static.data.gov.hk/covid-vaccine/summary.csv'

    vac_data = requests.get(vac_url).content
    vac = pd.read_csv(io.StringIO(vac_data.decode('utf-8')),
                      usecols=['firstDoseTotal', 'firstDosePercent',
                               'secondDoseTotal', 'secondDosePercent',
                               'latestDaily', 'sevenDayAvg', 
                               'firstDoseDaily', 'secondDoseDaily', 
                               'totalDosesAdministered']).fillna(0)

    return cbc, cum, vac

def main():

    header_html = "<h1>covid-hk</h1><p><small>the simple tracker for covid cases in HK</small></p>"
    st.markdown(header_html, unsafe_allow_html=True)

    st.markdown('---')

    case_by_case_data, cumulative_data, vaccine_data = get_data()

    most_recent_available_date = []
    most_recent_available_date.append(case_by_case_data['report_date_d'].iloc[-1])
    for i in range(1,5):
        most_recent_available_date.append(most_recent_available_date[i-1]-datetime.timedelta(days=1))

    most_recent_cases = []
    for i in range(0,5):
        most_recent_cases.append(len(case_by_case_data[(case_by_case_data['report_date_d']==most_recent_available_date[i])]))

    hdr = most_recent_available_date[0].strftime('%a %d %b %Y')

    if most_recent_cases[0] == 1:
        case_or_cases = 'case'
    else:
        case_or_cases = 'cases'

    st.subheader(hdr)

    st_radial('Cases', value = most_recent_cases[0])

    first_dose_percent = vaccine_data['firstDosePercent'][0]
    first_dose_total = vaccine_data['firstDoseTotal'][0]
    second_dose_percent = vaccine_data['secondDosePercent'][0]
    second_dose_total = vaccine_data['secondDoseTotal'][0]

    st.markdown('---')

    st.subheader('Vaccinations')
    col1, col2 = st.columns(2)
    with col1:
        st_card('First dose', float(first_dose_percent[:4]), unit='%', show_progress=True)
        st_card('First dose numbers', int(first_dose_total), show_progress=True)
    with col2:
        st_card('Second dose', float(second_dose_percent[:4]), unit='%', show_progress=True)
        st_card('Second dose numbers', int(second_dose_total), show_progress=True)

    grouped_type_df = case_by_case_data.groupby(['report_date_d', 'type'], as_index=False)['age'].count()
    grouped_type_df.rename(columns={'report_date_d':'date', 'age':'count_of_type'}, inplace=True)


    st.markdown('---')

    st.markdown('''Breakdown of the {} {} on {}:'''.format(most_recent_cases[0], case_or_cases, hdr))
    st.write(case_by_case_data[case_by_case_data['report_date_d']==most_recent_available_date[0]].type.value_counts())

    st.subheader('Summary charts')

    row_count = cumulative_data.shape[0]
    day_count = st.slider('Most recent x days', 1, row_count, 90)

    grouped_chart = alt.Chart(grouped_type_df[(grouped_type_df['date']>=(most_recent_available_date[0]+datetime.timedelta(days=(-1*day_count))))], title='Daily cases by type').mark_bar().encode(
                    x=alt.X('date', axis=alt.Axis(format='%Y-%m-%d', title='Date', labelAngle=-90)),
                    y=alt.Y('count_of_type', axis=alt.Axis(title='Cases')),
                    color=alt.Color('type:N', legend=alt.Legend(orient="bottom"), scale=alt.Scale(scheme='dark2')),
                    tooltip = [alt.Tooltip(field='date', type='temporal', format='%Y-%m-%d'),
                                alt.Tooltip(field='type', type='nominal'),
                                alt.Tooltip(field='count_of_type', title='cases', type='quantitative', format=',')]
                    ).interactive()
    st.altair_chart(grouped_chart, use_container_width=True)

    new_df = grouped_type_df[(grouped_type_df['date']>=(most_recent_available_date[0]+datetime.timedelta(days=(-1*day_count))))].pivot(index='date', columns='type', values='count_of_type').fillna(value=0).reset_index().drop(columns=['date'])
    streamlit_apex_charts.bar_chart('title', new_df, stacked=True)

    st.markdown('---')
    st.markdown('''NB cases reported for a specific date are the cases announced on that date, as of 00:00, and so represent cases in the preceding 24 hours''')
    st.markdown('---')
    st.markdown('''<small>Data source files: [data.gov.hk](https://data.gov.hk/en-data/dataset/hk-dh-chpsebcddr-novel-infectious-agent)</small>
                ''', unsafe_allow_html=True)
    png_html = get_img_with_href('GitHub-Mark-32px.png', 'https://github.com/daniellewisDL/covid-hk')
    st.markdown(png_html, unsafe_allow_html=True)
    png_html = get_img_with_href('GitHub-Mark-Light-32px.png', 'https://github.com/daniellewisDL/covid-hk')
    st.markdown(png_html, unsafe_allow_html=True)

    return None

if __name__ == '__main__':
    main()
