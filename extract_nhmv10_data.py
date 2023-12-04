"""
This script is used to extract NHM modeled flows from
the NHMv1.0 dataset to be used as Pywr-DRB model inputs. 
Data is export to CSV.

The method follows:
1.0 Get the IDs for all segments in the DRB
    1.1 Load the USGS geospatial fabric (GFv1.1) and DRB boundary
    1.2 Clip the GF using the boundary to identify all DRB relevant info.
2.0 Load and extract the NHM data of interest
    2.1 Load the .tar and get file members
    2.2 Extract files of interest
    2.3 Filter the data for DRB relevant values
3.0 Export CSVs

DATA:
The Geospatial Fabric (GFv1.1) data (1GB) is available here:
https://www.sciencebase.gov/catalog/item/5e29d1a0e4b0a79317cf7f63

The NHM-PRMS data must be downloaded here:
https://www.sciencebase.gov/catalog/item/5d826f6ae4b0c4f70d05913f

"""

import tarfile
import netCDF4 as nc
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib as mpl
import sys
import itertools

pywrdrb_dir = '../Pywr-DRB/'
sys.path.append(pywrdrb_dir)
from pywrdrb.pywr_drb_node_data import nhm_site_matches, immediate_downstream_nodes_dict, obs_pub_site_matches

NHM_DATA_DIR = 'C:/Users/tja73/Downloads'
re_extract = False

# Constants
cms_to_mgd = 22.82
cm_to_mg = 264.17/1e6
cfs_to_mgd = 0.64631688969744

# Load DRB and GF geospatial
crs = 4386
drb = gpd.read_file(f'{pywrdrb_dir}DRB_spatial/DRB_shapefiles/drb_bnd_polygon.shp').to_crs(crs)
gf = gpd.read_file(f'./GFv1.1.gdb/').to_crs(crs)
# gf_poi = gpd.read_file(f'./gfv11/gfv11.shp').to_crs(crs)

# Load metadata
nhm_to_gf_hru = pd.read_csv('./data/nhm_to_GFv1.1_HRU.csv', sep =',')
nhm_to_gf_seg = pd.read_csv('./data/nhm_to_GFv1.1_SEG.csv', sep =',')

nhm_gage_ids = pd.read_csv("./data/poi_gage_id.csv", index_col=0)
nhm_seg_ids = pd.read_csv("./data/poi_gage_segment.csv", index_col=0)


nhm_gage_segments = pd.concat([nhm_gage_ids, nhm_seg_ids], axis=1)
nhm_gage_segments.columns = ['gage_id', 'nhm_segment_id']
nhm_gage_segments['gage_id'] = [f'0{site_id}' for site_id in nhm_gage_segments['gage_id'].values]

# Clip the GF to DRB
gf_drb = gpd.clip(gf, drb)

# Store & export DRB relevant segment IDs
drb_segment_ids = gf_drb['nsegment_v1_1']
drb_nhm_gage_segments = nhm_gage_segments.loc[nhm_gage_segments['nhm_segment_id'].isin(drb_segment_ids)]
drb_nhm_gage_segments.to_csv('./outputs/drb_nhm_gage_segment_ids.csv', sep=',')


## Load the NHM data from .tar file location
if re_extract:

    # Open and store file names
    tar = tarfile.open(f'{NHM_DATA_DIR}/byHRU_musk_obs.tar')
    all_names = tar.getnames()
    all_members = tar.getmembers()

    # Extract just the NetCDF values of interest
    extract_member_indices = [7, 33, 36]
    extract_files = ['hru_outflow', 'seg_outflow', 'seg_upstream_inflow']

    for i in extract_member_indices:
        tar.extract(all_members[i], path = './outputs/')
    tar.close()

    ## HRU Outflow
    hru_data = nc.Dataset(f'./outputs/netcdf/hru_outflow.nc')

    # Store values
    vals = hru_data['hru_outflow'][:]
    hru_ids = hru_data['hru'][:]

    # Make a dataframe
    time_index = pd.date_range('1980-10-01', periods = 13241, freq = 'D')
    hru_outflow_df = pd.DataFrame(vals, index = time_index, columns = hru_ids)

    # Pull just DRB locations
    drb_hru_outflow = hru_outflow_df.loc[:, drb_segment_ids] * cfs_to_mgd

    # Export
    drb_hru_outflow.to_csv('./outputs/csv/drb_hru_outflow_mgd.csv', sep = ',')

    
    ## Segment Outflow
    seg_data = nc.Dataset(f'./outputs/netcdf/seg_outflow.nc')

    # Store values
    vals = seg_data['seg_outflow'][:]
    seg_ids = seg_data['segment'][:]

    # Make a dataframe
    seg_outflow_df = pd.DataFrame(vals, index = time_index, columns = seg_ids)

    # Pull just DRB locations
    drb_seg_outflow = seg_outflow_df.loc[:, drb_segment_ids] * cfs_to_mgd

    # Export
    drb_seg_outflow.to_csv('./outputs/csv/drb_seg_outflow_mgd.csv', sep = ',')
    drb_seg_outflow.to_hdf(f'./outputs/hdf/drb_seg_outflow_mgd.hdf5', key = 'df', mode = 'w')
    
    
## Retrieve and export Pywr-DRB nodal inflows
# Load the segment outflow which was previous extracted
drb_seg_outflow = pd.read_hdf(f'./outputs/hdf/drb_seg_outflow_mgd.hdf5', key = 'df')

## Retrieve just Pywr-DRB relevant flows
# Node inflows
pywr_drb_sites = []
for sites in nhm_site_matches.values():
    for s in sites:
        pywr_drb_sites.append(s)

# NHM flows that match gages in PywrDRB (Points of Interest)
for node, gage_ids in obs_pub_site_matches.items():
    if gage_ids:
        for g_id in gage_ids:
            nhm_gage_poi_id = drb_nhm_gage_segments[drb_nhm_gage_segments.gage_id == g_id].nhm_segment_id
            if len(nhm_gage_poi_id) > 0:
                print(f'NHM equivalent POI {nhm_gage_poi_id.values[0]} found for {node}')
                pywr_drb_sites.append(str(nhm_gage_poi_id.values[0]))

pywr_drb_nhm_flows = drb_seg_outflow.loc[:, pywr_drb_sites]

# Get rid of duplicate column from `delDRCanal` and `delTrenton`
pywr_drb_nhm_flows = pywr_drb_nhm_flows.T.drop_duplicates().T

# Export
pywr_drb_nhm_flows.to_csv(f'./outputs/csv/streamflow_daily_nhmv10_mgd.csv', sep = ',')
pywr_drb_nhm_flows.to_csv(f'{pywrdrb_dir}input_data/modeled_gages/streamflow_daily_nhmv10_mgd.csv', sep = ',')