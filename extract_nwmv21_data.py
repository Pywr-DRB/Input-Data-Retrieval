import os
import tarfile
import netCDF4 as nc
import xarray
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl
import sys
import itertools

from directories import PYWRDRB_DIR, NWM_DIR
OUTPUT_DIR = './datasets/NWMv21/'

sys.path.append(PYWRDRB_DIR)

# Constants
cms_to_mgd = 22.82
cm_to_mg = 264.17/1e6
cfs_to_mgd = 0.64631688969744

crs = 4386
drb = gpd.read_file(f'{PYWRDRB_DIR}DRB_spatial/DRB_shapefiles/drb_bnd_polygon.shp').to_crs(crs)

# Load NWM dataset 1979-2020
nwm_nwis = nc.Dataset(f'{NWM_DIR}nwmv21_nwis.nc')
print('NWMv21 NWIS dataset loaded...')

# Load unmanaged gauge metadata
unmanaged_gauge_metadata = pd.read_csv(f'./datasets/USGS/drb_unmanaged_usgs_metadata.csv', dtype={'site_no':str})
all_gauge_metadata = pd.read_csv(f'./datasets/USGS/drb_all_usgs_metadata.csv', dtype={'site_no':str})

# Pull longitude and latitude
long = nwm_nwis['longitude'][:].data
lat = nwm_nwis['latitude'][:].data
feature_id = nwm_nwis['feature_id'][:].data
time_index = nwm_nwis['time'][:].data

# Find NWM points that match unmanaged gauges
nwm_gauge_matches = {}
nwm_gauge_matches['comid'] = []
nwm_gauge_matches['site_no'] = []
nwm_gauge_matches['lat'] = []
nwm_gauge_matches['long'] = []

nwm_gauge_matches_idx = []
for i,id in enumerate(feature_id):
    if id in list(all_gauge_metadata['comid']):
        nwm_gauge_matches['comid'].append(id)
        nwm_gauge_matches['site_no'].append(all_gauge_metadata.loc[all_gauge_metadata['comid']==id, 'site_no'].values[0])
        nwm_gauge_matches['lat'].append(lat[i])
        nwm_gauge_matches['long'].append(long[i])
        
        nwm_gauge_matches_idx.append(i)

    # TODO: A new reach for Nockamixon: the original is bad    
    # elif str(id) == '2591219':
        
    
    elif str(id) == '4147956':

        # Neversink is getting dropped because it is not in the unmanaged gauge list somereason
        station_no =  '01435000'
        
        nwm_gauge_matches['comid'].append(id)
        nwm_gauge_matches['site_no'].append(station_no)
        nwm_gauge_matches['lat'].append(lat[i])
        nwm_gauge_matches['long'].append(long[i])
        nwm_gauge_matches_idx.append(i)
        
# Pull streamflow data
for i in nwm_gauge_matches_idx:
    if i == nwm_gauge_matches_idx[0]:
        nwm_gauge_data = pd.DataFrame(nwm_nwis['streamflow'][i,:].data*cms_to_mgd, index=time_index, columns=[feature_id[i]])
    else:
        nwm_gauge_data[feature_id[i]] = pd.DataFrame(nwm_nwis['streamflow'][i,:].data*cms_to_mgd, index=time_index)
        
## Aggregate to daily flow in MGD
# Default time is hours since 1970-02-01 00:00:00
# source: https://www.sciencebase.gov/catalog/item/612e264ed34e40dd9c091228
print('Aggregating to daily flow...')
datetime_index = pd.date_range(start='1979-02-01 00:00:00', end='2020-12-31', 
                               freq='D')

# Pull data for each day
nwm_streamflow = pd.DataFrame(index=datetime_index, columns=nwm_gauge_data.columns)
for i,d in enumerate(datetime_index):
    nwm_streamflow.loc[d,:] = nwm_gauge_data.iloc[(i*24):(i*24+24),:].mean(axis=0)
    
# Change columns to strings
nwm_streamflow.columns = nwm_streamflow.columns.astype(str)

## Export
# Streamflow
nwm_streamflow.to_csv(f'{OUTPUT_DIR}/nwmv21_gauge_streamflow_daily_mgd.csv')

# Metadata
nwm_gauge_matches = pd.DataFrame(nwm_gauge_matches)
nwm_gauge_matches.to_csv(f'{OUTPUT_DIR}/nwmv21_gauge_metadata.csv', index=False)
print(f'NWMv21 NWIS streamflow and metadata exported to {OUTPUT_DIR}!')