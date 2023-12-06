"""
This file contains the paths to directories containing different data sources.
All paths are relative from this file's location.
"""
import os

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

