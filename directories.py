"""
This file contains the paths to directories containing different data sources.
All paths are relative from this file's location.
"""
import os

# PYWRDRB_DATA_DIR cotains processed data used in the pywrdrb package/model
# this data will be stored in the source code within: Pywr-DRB/src/pywrdrb/data/
# the data has corresponding subfolders for different data sources.
# The Input-Data-Retrieval scripts are used to process and save this data in PYWRDRB_DATA_DIR
# while matching the structure of the pywrdrb/data/ folder.
# We can then later move the data to the Pywr-DRB/src/pywrdrb/data/ folder
# this is done manually for now, but we can automate this in the future
PYWRDRB_DATA_DIR = './datasets/pywrdrb_data/'



# pwrdrb source code
# folder should contain ./pywrdrb/*
PYWRDRB_DIR = '../Pywr-DRB/'

# The NHM-PRMS data must be downloaded here:
# https://www.sciencebase.gov/catalog/item/5d826f6ae4b0c4f70d05913f
NHM_DIR = 'C:/Users/tja73/Downloads'
necessary_files = ['byHRU_musk_obs.tar']


# The Geospatial Fabric (GFv1.1) data (1GB) is available here:
# https://www.sciencebase.gov/catalog/item/5e29d1a0e4b0a79317cf7f63
GEO_FABRIC_DIR = '.'
necessary_files = []


# National Water Model V2.1 (NWMv2.1) NWIS Retrospective:
# https://www.sciencebase.gov/catalog/item/612e264ed34e40dd9c091228
NWM_DIR = '../NWMv21/'
necessary_files = ['nwmv21_nwis.nc']
for file in necessary_files:
    assert(file in os.listdir(NWM_DIR)), f'Required file {file} not found in {NWM_DIR}'

# Contains various WRF-Hydro model outputs, as provided by Aubrey Duggar at NCAR
WRFHYDRO_DIR = './datasets/WRF-Hydro/'


# Contains geospatial data (catchment boundaries, etc.)
SPATIAL_DIR = './datasets/Spatial/'

# Contains demand data
DEMAND_DIR = './datasets/Demand/'
