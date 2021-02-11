import json
import altair as alt
import pandas as pd
import numpy as np
from flask import g
import objects
from objects import Appointments, Logs, Procedures, Clinics

class Dashboard:
        
    def dashboard1(self): 
        li=[]
        alist5 = []
        app_df = Appointments().dashboard_func()
        log_df = Logs().dashboard_func()
        log_df1 = log_df.reset_index().drop(columns=['index','key','what'])
        log_df1['when'] = pd.to_datetime(log_df1.when, utc=True)
        log_df2 = log_df1.set_index(['ref_type','log_type','when']).sort_index()
        log_df3 = log_df2.loc[('APPOINTMENT','COMPLETED'),:].reset_index('when').sort_index()
        for x in log_df3['ref_key']:
            li.append(x)
        app_df1 = app_df.reindex(li)
        app_df2 = app_df1.reset_index().dropna()
        app_df3 = app_df2.loc[:,['index','procedures']]
        app_dict = app_df3.to_dict(orient='index')
        for a in app_dict:
            for p in app_dict[a]['procedures']:
                alist5.append({'appointment':app_dict[a]['index'], 'procedure':p})
        app_df4 = pd.DataFrame(alist5)
        app_df7 = app_df4.set_index('appointment').join(log_df3.set_index('ref_key'))\
                .reset_index().rename(columns={'index':'appointment'})\
                .set_index('when')
        app_df8 = pd.DataFrame(app_df7.resample('1W').appointment.nunique()).reset_index()
        plot = alt.Chart(app_df8).mark_bar().encode(x='when',y='appointment')
        result = plot.to_dict()
        return result

    def dashboard2(self):
        li=[]
        alist5 = []
        app_df = Appointments().dashboard_func()
        log_df = Logs().dashboard_func()
        pro_df  = Procedures().dashboard_func()
        log_df1 = log_df.reset_index().drop(columns=['index','key','what'])
        log_df1['when'] = pd.to_datetime(log_df1.when, utc=True)
        log_df2 = log_df1.set_index(['ref_type','log_type','when']).sort_index()
        log_df3 = log_df2.loc[('APPOINTMENT','COMPLETED'),:].reset_index('when').sort_index()
        for x in log_df3['ref_key']:
            li.append(x)
        app_df1 = app_df.reindex(li)
        app_df2 = app_df1.reset_index().dropna()
        app_df3 = app_df2.loc[:,['index','procedures']]
        app_dict = app_df3.to_dict(orient='index')
        for a in app_dict:
            for p in app_dict[a]['procedures']:
                alist5.append({'appointment':app_dict[a]['index'], 'procedure':p})
        app_df4 = pd.DataFrame(alist5)
        pro_df1 = pro_df.loc[app_df4['procedure']]
        pro_df2 = pro_df1.reset_index().rename(columns={'index':'procedure'})
        prolog_df = pro_df2.set_index('appointment').join(log_df3.set_index('ref_key'))\
                    .reset_index().rename(columns ={'index':'appointment'})\
                    .set_index('when')
        prolog_df1 = prolog_df.loc[:,('appointment','procedure','scan_type')]
        prolog_df1.reset_index().when.dt.date
        adf1 = prolog_df1.reset_index()
        adf1['day'] = adf1.when.dt.date
        adf2 = adf1.loc[:,['procedure','scan_type','day']]
        adf2['pnum'] = adf2.procedure.map(lambda p: 1)
        adf2['date'] = pd.to_datetime(adf2.day)
        adf3 = adf2.drop(columns=['day','procedure'])
        plot = alt.Chart(adf3).mark_bar().encode(x='date:T',y='sum(pnum)',color='scan_type')
        result = plot.to_dict()
        return result

    def dashboard3(self):
        app_df = Appointments().dashboard_func()
        log_df = Logs().dashboard_func()
        clinics_df = Clinics().dashboard_func()
        log_df1 = log_df.reset_index().drop(columns=['index','key','what'])
        log_df1['when'] = pd.to_datetime(log_df1.when, utc=True)
        log_df2 = log_df1.set_index(['ref_type','log_type','when']).sort_index()
        log_df3 = log_df2.loc[('APPOINTMENT','COMPLETED'),:].reset_index('when').sort_index()
        stage1 = log_df3.reset_index().set_index('ref_key')\
                     .join(app_df)\
                     .loc[:,['when','clinic']]
        data_df = stage1.reset_index().set_index('clinic')\
            .join(clinics_df)\
            .loc[:,['when','name','ref_key']]\
            .reset_index()
        plot = alt.Chart(data_df).mark_bar().encode(x='monthdate(when):O',y='count(ref_key)',color='name')
        result = plot.to_dict()
        return result

    def dashboard4(self):
        # app_df = Appointments().dashboard_func()
        df = Logs().dashboard_func()
        df.reset_index().set_index('key')
        a = df.reset_index().set_index(['ref_type','ref_key','log_type']).sort_index()\
            .loc[('APPOINTMENT',)]
        b = a.when.to_frame()\
            .loc[pd.IndexSlice[:,['ARRIVED','CHECKED_IN','IN_PROGRESS','COMPLETED']],:]\
            .unstack('log_type').when
        b.ARRIVED = pd.to_datetime(b.ARRIVED)
        b.CHECKED_IN = pd.to_datetime(b.CHECKED_IN)
        b.IN_PROGRESS = pd.to_datetime(b.IN_PROGRESS)
        b.COMPLETED = pd.to_datetime(b.COMPLETED)
        c = b.loc[:,['CHECKED_IN','IN_PROGRESS','COMPLETED']].copy()
        for col in c.columns:
            u = (c[col] - b.ARRIVED)
            c[col] = 24*60*60*u.dt.days + u.dt.seconds
            
        data = []
        for k,row in c.iterrows():
            data.append({
                'key': k,
                'state': 'ARRIVED',
                'start': 0,
                'end': row.CHECKED_IN
            })
            data.append({
                'key': k,
                'state': 'CHECKED_IN',
                'start': row.CHECKED_IN,
                'end': row.IN_PROGRESS
            })
            data.append({
                'key': k,
                'state': 'IN_PROGRESS',
                'start': row.IN_PROGRESS,
                'end': row.COMPLETED
            })
            
        appt_source = pd.DataFrame(data).dropna()

        y_axis = alt.Axis(
            title='Question',
            offset=5,
            ticks=False,
            minExtent=60,
            domain=False
        )

        plot = alt.Chart(appt_source).mark_bar().encode(x='start:T', x2='end:T', y='key:N', color=alt.Color('state:N'))

        result = plot.to_dict()
        return result

    def dashboard5(self):
        df = Logs().dashboard_func()
        df1 = df.reset_index().drop(columns=['index','key'])
        df1['when'] = pd.to_datetime(df1.when)
        df2 = df1.set_index(['ref_type','log_type','when']).sort_index()

        df3 = df2.loc[('APPOINTMENT','CANCELLED'),:].reset_index('when').sort_index()

        plot = alt.Chart(df3).mark_bar().encode(
            x='monthdate(when):O',
            y='count(who):O',
            color='what'
        )
        result = plot.to_dict()
        return result

    def dashboard6(self):
        df = Logs().dashboard_func()
        df.reset_index().set_index('key')
        a = df.reset_index().set_index(['ref_type','ref_key','log_type']).sort_index()\
            .loc[('APPOINTMENT',)]
        b = a.when.to_frame()\
            .loc[pd.IndexSlice[:,['IN_PROGRESS']],:]\
            .unstack('log_type').when
        b.IN_PROGRESS = pd.to_datetime(b.IN_PROGRESS)
        t1 = b.IN_PROGRESS
        t2 = t1.reset_index().drop(columns=['ref_key'])

        plot = alt.Chart(t2).mark_circle().encode(
            y='hours(IN_PROGRESS):O',
            x='day(IN_PROGRESS):O',
            size='count(IN_PROGRESS):Q'
        )
        result = plot.to_dict()
        return result

    def dashboard7(self):
        df = Logs().dashboard_func()
        df.reset_index().set_index('key')
        a = df.reset_index().set_index(['ref_type','ref_key','log_type']).sort_index()\
            .loc[('APPOINTMENT',)]

        b = a.when.to_frame()\
            .loc[pd.IndexSlice[:,['ARRIVED','CHECKED_IN','IN_PROGRESS','COMPLETED']],:]\
            .unstack('log_type').when
        b.ARRIVED = pd.to_datetime(b.ARRIVED)
        b.CHECKED_IN = pd.to_datetime(b.CHECKED_IN)
        b.IN_PROGRESS = pd.to_datetime(b.IN_PROGRESS)
        b.COMPLETED = pd.to_datetime(b.COMPLETED)

        t1 = (b.CHECKED_IN - b.ARRIVED)
        d1 = 24*60*60*t1.dt.days + t1.dt.seconds

        t2 = (b.IN_PROGRESS - b.CHECKED_IN)
        d2 = 24*60*60*t2.dt.days + t2.dt.seconds

        t3 = (b.COMPLETED - b.IN_PROGRESS)
        d3 = 24*60*60*t3.dt.days + t3.dt.seconds

        data = pd.DataFrame({'diff1':d1, 'diff2':d2, 'diff3':d3}).dropna()

        plot = alt.Chart(data).transform_fold(
            ['diff1', 'diff2', 'diff3'],
            as_=['Appointment', 'Time']
        ).mark_area(
            opacity=0.3,
            interpolate='step'
        ).encode(
            alt.X('Time:Q', bin=alt.Bin(maxbins=20)),
            alt.Y('count()', stack=None),
            alt.Color('Appointment:N')
        )
        result = plot.to_dict()
        return result
        
        

