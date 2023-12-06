"""
Queries streamflow data from the USGS NWIS, 
identifies data within the DRB and removes streamflows which are labeled as being 
downstream of reservoirs.

Data is retrieved from 1900 onward to the present. 
"""

import sys
import itertools
import numpy as np
import pandas as pd
import geopandas as gpd

from pygeohydro import NWIS
import pynhd as pynhd

OUTPUT_DIR = './datasets/USGS/'
PYWRDRB_DIR = '../Pywr-DRB/'
sys.path.append(PYWRDRB_DIR)
from pywrdrb.pywr_drb_node_data import obs_site_matches, obs_pub_site_matches
pywrdrb_obs_gauges = [x for x in obs_pub_site_matches.values() if x is not None]
pywrdrb_obs_gauges = list(itertools.chain.from_iterable(pywrdrb_obs_gauges))

print(f'PywrDRB has {pywrdrb_obs_gauges} gauges.')

export_to_pywrdrb = False
 
### Setup
dates = ('1900-01-01', '2022-12-31')

filter_drb = True
bbox = (-77.8, 37.5, -74.0, 44.0)
boundary = 'drb' if filter_drb else 'regional'


def filter_drb_sites(x, 
                     sdir = f'{PYWRDRB_DIR}/DRB_spatial/DRB_shapefiles'):
    """Filters USGS gauge data to remove gauges outside the DRB boundary.

    Args:
        x (pd.DataFrame): A dataframe with gauges including columns "long" and "lat" with location data. 
        sdir (str, optional) The location of the folder containing the DRB shapefile: drb_bnd_polygon.shp
    Returns:
        pd.DataFrame: Dataframe containing gauge data, for gauges within the DRB boundary
    """
    crs = 4386

    drb_boarder = gpd.read_file(f'{sdir}/drb_bnd_polygon.shp')
    drb_boarder = drb_boarder.to_crs(crs)
    x_all = gpd.GeoDataFrame(x, geometry = gpd.points_from_xy(x.long, x.lat, crs = crs))
    x_filtered = gpd.clip(x_all, drb_boarder)
    return x_filtered



### Request and save specific pywrdrb gauge flows
## Get historic observations that exist (including management)
pywrdrb_stations = []
for node, sites in obs_site_matches.items():
    if sites:
        for s in sites:
            pywrdrb_stations.append(s)

nwis = NWIS()
Q_pywrdrb = nwis.get_streamflow(pywrdrb_stations, dates)
Q_pywrdrb.index = pd.to_datetime(Q_pywrdrb.index.date)

for s in pywrdrb_stations:
    assert(f'USGS-{s}' in Q_pywrdrb.columns),'PywrDRB gauge {s} is missing from the data.'

# Export
Q_pywrdrb.to_csv(f'{OUTPUT_DIR}/streamflow_daily_usgs_cms.csv', sep=',')
if export_to_pywrdrb:
    Q_pywrdrb.to_csv(f'{PYWRDRB_DIR}/input_data/usgs_gages/streamflow_daily_usgs_1950_2022_cms.csv', sep=',')



### Unmanaged flows: For the prediction at ungauged or managed locations
### we want only unmanaged flow data.  The following retrieves, filters, and exports unmanaged flows across the basin. 
### 1: Query USGS data ###
# Use the national water info system (NWIS)
nwis = NWIS()
print("Initialized")

# Send a query_request for all gage info in the bbox
query_request = {"bBox": ",".join(f"{b:.06f}" for b in bbox),
                    "hasDataTypeCd": "dv",
                    "outputDataTypeCd": "dv"}

query_result = nwis.get_info(query_request, expanded= False, nhd_info= False)

# Filter non-streamflow stations
query_result = query_result.query("site_tp_cd in ('ST','ST-TS')")
query_result = query_result[query_result.parm_cd == '00060']  # https://help.waterdata.usgs.gov/parameter_cd?group_cd=PHY
query_result = query_result.reset_index(drop = True)

stations = list(set(query_result.site_no.tolist()))
print(f"Gage data gathered, {len(stations)} USGS streamflow gauges found in date range.")


### Location data (long,lat)
gage_data = query_result[['site_no', 'dec_long_va', 'dec_lat_va', 'begin_date', 'end_date']]
gage_data.columns = ['site_no', 'long', 'lat', 'begin_date', 'end_date']
gage_data.index = gage_data['site_no']
gage_data= gage_data.drop('site_no', axis=1)


### 2: Filter data ###
## Remove sites outside the DRB boundary
if filter_drb:
    gage_data = filter_drb_sites(gage_data)
gage_data = gage_data[~gage_data.index.duplicated(keep = 'first')]
stations = gage_data.index.to_list()
print(f'{len(stations)} streamflow gauges after filtering.')

## Remove managed sites
# To do this, wee will use NLDI attributes to find managed sites
# Initialize the NLDI database
nldi = pynhd.NLDI()

# Get COMID for each gauge
gage_comid = pd.DataFrame(index = gage_data.index, columns=['comid', 'reachcode', 'comid-long', 'comid-lat'])
for st in gage_data.index:
    coords = (gage_data.loc[st, ['long']].values[0], gage_data.loc[st, ['lat']].values[0])
    try:
        found = nldi.comid_byloc(coords)
        gage_comid.loc[st, ['comid']] = found.comid.values[0]
        gage_comid.loc[st, ['reachcode']] = found.reachcode.values[0]
        gage_comid.loc[st, ['comid-long']] = found.geometry.x[0]
        gage_comid.loc[st, ['comid-lat']] = found.geometry.y[0]
    except:
        print(f'Error getting COMID for site {st}')
        
gage_data = pd.concat([gage_data, gage_comid], axis=1)
gage_data = gage_data.dropna(axis=0)
gage_data["comid"] = gage_data["comid"].astype('int')

# Specific characteristics of interest, for now we only want reservoir information
all_characteristics = nldi.valid_characteristics
reservoir_characteristics = ['CAT_NID_STORAGE2013', 'CAT_NDAMS2013', 'CAT_MAJOR2013', 'CAT_NORM_STORAGE2013']
TOT_reservoir_characteristics = ['TOT_NID_STORAGE2013', 'TOT_NDAMS2013', 'TOT_MAJOR2013', 'TOT_NORM_STORAGE2013']

## Use the station IDs to retrieve basin information
tot_chars = nldi.getcharacteristic_byid(gage_data.comid, fsource = 'comid', 
                                        char_type= "tot", char_ids= TOT_reservoir_characteristics)
local_chars = nldi.getcharacteristic_byid(gage_data.comid, fsource = 'comid',
                                            char_type= "local", char_ids= reservoir_characteristics)

cat_chars = pd.concat([tot_chars, local_chars], axis=1)

cat = cat_chars
cat['comid'] = cat.index
print(f'Found characteristics for {cat_chars.shape} of {gage_data.shape} basins.')


## Remove sites that have reservoirs upstream
gage_with_cat_chars = pd.merge(gage_data, cat, on = "comid")
gage_with_cat_chars.index = gage_data.index
managed_stations = []
for i, st in enumerate(gage_data.index):
    if gage_with_cat_chars.loc[st, TOT_reservoir_characteristics].sum() > 0:
        if st not in pywrdrb_obs_gauges:
            managed_stations.append(st)
    
# Take data from just unmanaged
unmanaged_gauge_data = gage_data.drop(managed_stations)
print(f'{len(managed_stations)} of the {gage_data.shape[0]} gauge stations are managed and being removed.')

# Export gage_data
gage_data.to_csv(f'{OUTPUT_DIR}/{boundary}_all_usgs_metadata.csv', sep=',')
unmanaged_gauge_data.to_csv(f'{OUTPUT_DIR}/{boundary}_unmanaged_usgs_metadata.csv', sep=',')
