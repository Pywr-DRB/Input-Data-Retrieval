"""
This script is used to extract Pywr-DRB input data from various WRF-Hydro model results.

This scipt assumes you do NOT want to use the modeled reach streamflow with level-pool lakes on. 

For each WRF-Hydro configuration, there are 3 primary datasets available:
- Simulated flow with level-pool lakes on 
- Simulated flow with level-pool lakes off
- Level-pool Lake inflow, storage, output

For each configuration, the Pywr-DRB input will be either:
- Streamflow with lakes OFF (pywrdrb will simulate reservoir effect)
- Lake inflow for reservoir locations (assume the reservoir has a lake object)

The output files will have the names:
'streamflow_daily_wrf_{climate}_{calibration}_{landcover}.csv'
    This contains the flows with lakes off

'lakes_daily_wrf_{climate}_{calibration}_{landcover}.csv'
    This contains the lake inflow for reservoirs nodes

"""
import netCDF4 as nc
import pandas as pd
import sys
import os

from directories import WRFHYDRO_DIR, PYWRDRB_DIR

# Constants
cms_to_mgd = 22.82
cm_to_mg = 264.17/1e6
cfs_to_mgd = 0.64631688969744

# Model configuration options:
climate_opts = ['1960s', 'aorc', '2050s']
calibration_opts = ['calib', 'uncalib']
landcover_opts = ['foresce1960', 'foresce2010', 'foresce2050_bau_rcp85', 'nlcd2016']
levelpool_opts = ['pool', 'no_pool']
flowtype_ops = ['reaches', 'lakes']

# E.g., specific model configuration
config_args = ['climate', 'calibration', 'landcover', 'levelpool', 'flowtype']
config = {
    'climate': '1960s',
    'calibration': 'calib',
    'landcover': 'foresce1960',
    'levelpool': 'pool',
    'flowtype': 'reaches'
}

# Dates depending on config climate:
date_ranges = {
    '1960s': ('1959-10-01', '1969-12-31'),
    'aorc': ('1979-10-01', '2021-12-31'),
    '2050s': ('2051-10-01', '2061-12-31'),
}



## WRF-Hydro COMID numbers; taken from nhm_site_matches
wrf_hydro_site_matches = {'cannonsville': ['2613174'],    # Lake inflow
                    'pepacton': ['1748473'],        # Lake inflow
                    'neversink': ['4146742'],       # Lake inflow
                    'wallenpaupack': ['2741600'],   # Lake inflow
                    'prompton': ['2739068'],        # Lake inflow
                    'shoholaMarsh': ['120052035'],  # Lake inflow
                    'mongaupeCombined': ['4148582'],    # Lake inflow
                    'beltzvilleCombined': ['4186689'],  # Lake inflow
                    'fewalter': ['4185065'],        # Lake inflow
                    'merrillCreek': ['2588031'],    # No NWM lake; using available segment flow
                    'hopatcong': ['2585287'],       # Lake inflow
                    'nockamixon': ['2591099'],      # No NWM lake; using available segment flow  2591187 2591219
                    'assunpink': ['2589015'],       # Lake inflow
                    'ontelaunee': ['4779981'],      # Lake inflow
                    'stillCreek': ['4778721'],      # Lake inflow
                    'blueMarsh': ['4782813'],       # Lake inflow
                    'greenLane': ['4780087'],       # Lake inflow 
                    '01425000': ['2614238'],
                    '01417000': ['1748727'],
                    'delLordville': ['2617364'],
                    '01436000': ['4147432'],
                    '01433500': ['4150156'],
                    'delMontague': ['4151628'],
                    '01449800': ['4187341'],
                    '01447800': ['4186403'],
                    'delDRCanal': ['2590277'],
                    'delTrenton': ['2590277'],
                    '01463620': ['2590117'],
                    'outletAssunpink': ['2590137'],
                    '01470960': ['4783213'],
                    'outletSchuylkill': ['4784841']
                    }

pywrdrb_wrf_hydro_flowtypes = {
    'cannonsville': 'lakes',    # Lake inflow
    'pepacton': 'lakes',        # Lake inflow
    'neversink': 'lakes',       # Lake inflow
    'wallenpaupack': 'lakes',   # Lake inflow
    'prompton': 'lakes',        # Lake inflow
    'shoholaMarsh': 'lakes',  # Lake inflow
    'mongaupeCombined': 'lakes',    # Lake inflow
    'beltzvilleCombined': 'lakes',  # Lake inflow
    'fewalter': 'lakes',        # Lake inflow
    'merrillCreek': 'reaches',    # No NWM lake; using available segment flow
    'hopatcong': 'lakes',       # Lake inflow
    'nockamixon': 'reaches',      # No NWM lake; using available segment flow  2591187 2591219
    'assunpink': 'lakes',       # Lake inflow
    'ontelaunee': 'lakes',      # Lake inflow
    'stillCreek': 'lakes',      # Lake inflow
    'blueMarsh': 'lakes',       # Lake inflow
    'greenLane': 'lakes',       # Lake inflow 
    '01425000': 'reaches',
    '01417000': 'reaches',
    'delLordville': 'reaches',
    '01436000': 'reaches',
    '01433500': 'reaches',
    'delMontague': 'reaches',
    '01449800': 'reaches',
    '01447800': 'reaches',
    'delDRCanal': 'reaches',
    'delTrenton': 'reaches',
    '01463620': 'reaches',
    'outletAssunpink': 'reaches',
    '01470960': 'reaches',
    'outletSchuylkill': 'reaches'
    }

# Function to get full filepath for a specific config
def get_WRF_Hydro_output_filename(config):
    inval_option_msg = 'Invalid option specified for {0}. Options: {1}'
    assert(config['climate'] in climate_opts), inval_option_msg.format('climate', climate_opts)
    assert(config['calibration'] in calibration_opts), inval_option_msg.format('calibration', calibration_opts)
    assert(config['landcover'] in landcover_opts), inval_option_msg.format('landcover', landcover_opts)
    assert(config['levelpool'] in levelpool_opts), inval_option_msg.format('levelpool', levelpool_opts)
    assert(config['flowtype'] in flowtype_ops), inval_option_msg.format('flowtype', flowtype_ops)
    
    if config['climate'] == '1960s':
        subfolder = '1960s_climate/'
        climate_src = 'wrf' + config["climate"]
    elif config['climate'] == 'aorc':
        subfolder = 'current_climate/'
        climate_src = config["climate"]
    elif config['climate'] == '2050s':
        subfolder = '2050s_climate/'
        climate_src = 'wrf' + config["climate"]
    
    dir = WRFHYDRO_DIR + subfolder
    if config['levelpool'] == 'pool':
        fname = f'{dir}{config["flowtype"]}_daily_{config["calibration"]}_{config["landcover"]}_{climate_src}.nc'      
    else:
        fname = f'{dir}{config["flowtype"]}_daily_{config["calibration"]}_nolakes_{config["landcover"]}_{climate_src}.nc'
    return fname


def load_WRF_Hydro_data_from_config(config, 
                                    units='mgd', cms_to_mgd=cms_to_mgd,
                                    date_ranges=date_ranges):
    """
    Extracts WRF-Hydro data for a specific configuration and date range.
    """
    
    src_fname = get_WRF_Hydro_output_filename(config)
    
    # make sure file exists
    os.path.exists(src_fname), f'File {src_fname} not found.'
        
    # load
    wrf = nc.Dataset(src_fname)
    
    # pull features
    if config['flowtype'] == 'reaches':
        streamflow = wrf['streamflow'][:].data
    elif config['flowtype'] == 'lakes':
        streamflow = wrf['inflow'][:].data
        
    if units == 'mgd':
        streamflow = streamflow * cms_to_mgd
    elif units == 'cms':
        pass
    else:
        raise ValueError('Invalid units specified. Options: "mgd", "cms"')
    
    feature_id = wrf['feature_id'][:].data
    
    time = wrf['time'][:].data
    datetime = pd.date_range(start=date_ranges[config['climate']][0],
                                end=date_ranges[config['climate']][1],
                                freq='D')
    assert(len(time)==len(datetime)), 'Data "time" and provided datetime length mismatch.'
    
    wrf_df = pd.DataFrame(streamflow, 
                          index=datetime, columns=feature_id)
    wrf_df.columns = wrf_df.columns.astype(str)
    
    return wrf_df


def retrieve_pywrdrb_inputs_from_WRF_Hydro(climate, calib, landcover,
                                          wrf_hydro_site_matches,
                                          pywrdrb_wrf_hydro_flowtypes=pywrdrb_wrf_hydro_flowtypes,
                                          date_ranges=date_ranges,
                                          labelby_pywrdrb_nodes=False):
    """
    Extracts Pywr-DRB input data from WRF-Hydro model results.
    """
    config = {
        'climate': climate,
        'calibration': calib,
        'landcover': landcover,
    }
        
    # Load WRF-Hydro data for reaches with levelpool off
    config['flowtype'] = 'reaches'
    config['levelpool'] = 'no_pool'
    wrf_reaches_df = load_WRF_Hydro_data_from_config(config, date_ranges=date_ranges)
    
    # Load WRF-Hydro data for lake inflows
    config['flowtype'] = 'lakes'
    config['levelpool'] = 'pool'
    wrf_lakes_df = load_WRF_Hydro_data_from_config(config, date_ranges=date_ranges)
    
    output_columns = list(wrf_hydro_site_matches.keys()) if labelby_pywrdrb_nodes else [item for sublist in list(wrf_hydro_site_matches.values()) for item in sublist]
    wrf_pywrdrb_df = pd.DataFrame(index=wrf_reaches_df.index, columns=output_columns)
    
    for node, fid in wrf_hydro_site_matches.items():
        if pywrdrb_wrf_hydro_flowtypes[node] == 'reaches':
            node_flow = wrf_reaches_df[fid]
        elif pywrdrb_wrf_hydro_flowtypes[node] == 'lakes':
            node_flow = wrf_lakes_df[fid]
        
        if labelby_pywrdrb_nodes:
            wrf_pywrdrb_df.loc[:,node] = node_flow.values
        else:
            wrf_pywrdrb_df.loc[:,fid] = node_flow.values
    
    return wrf_pywrdrb_df

def get_export_filename(config):
    fname = f'{WRFHYDRO_DIR}streamflow_daily_wrf{config["climate"]}_{config["calibration"]}_{config["landcover"]}.csv'
    return fname


def retrieve_and_export_pywrdrb_input_from_WRF_Hydro_output(config,
                                                            wrf_hydro_site_matches,
                                                            pywrdrb_wrf_hydro_flowtypes=pywrdrb_wrf_hydro_flowtypes,
                                                            labelby_pywrdrb_nodes=False,
                                                            date_ranges=date_ranges,
                                                            return_df=False):
    """
    Exports Pywr-DRB input data to a CSV file.
    """
    export_fname = get_export_filename(config)
    
    df = retrieve_pywrdrb_inputs_from_WRF_Hydro(config['climate'], config['calibration'], config['landcover'], wrf_hydro_site_matches,
                                                pywrdrb_wrf_hydro_flowtypes=pywrdrb_wrf_hydro_flowtypes, labelby_pywrdrb_nodes=labelby_pywrdrb_nodes, 
                                                date_ranges=date_ranges)
    df.to_csv(export_fname)
    print(f'Exported Pywr-DRB input data to {export_fname}')
    return df if return_df else None







if __name__ == '__main__':
    
    
    
    ### Process different model configurations
    
    ## Current climate (AORC)
    print('Processing current climate (AORC) WRF-Hydro datasets...')
    config = {
        'climate': 'aorc',
        'calibration': 'calib',
        'landcover': 'nlcd2016',
    }

    retrieve_and_export_pywrdrb_input_from_WRF_Hydro_output(config, wrf_hydro_site_matches, 
                                                            labelby_pywrdrb_nodes=False, return_df=False)

    config = {
        'climate': 'aorc',
        'calibration': 'uncalib',
        'landcover': 'foresce2010',
    }
    retrieve_and_export_pywrdrb_input_from_WRF_Hydro_output(config, wrf_hydro_site_matches, 
                                                            labelby_pywrdrb_nodes=False, return_df=False)

    ## 1960s climate
    print('Processing 1960s climate WRF-Hydro datasets...')
    config = {
        'climate': '1960s',
        'calibration': 'calib',
        'landcover': 'nlcd2016',
    }
    retrieve_and_export_pywrdrb_input_from_WRF_Hydro_output(config, wrf_hydro_site_matches, 
                                                            labelby_pywrdrb_nodes=False, return_df=False)
    
    
    ## 2050s climate
    print('Processing 2050s climate WRF-Hydro datasets...')
    config = {
        'climate': '2050s',
        'calibration': 'calib',
        'landcover': 'nlcd2016',
    }
    retrieve_and_export_pywrdrb_input_from_WRF_Hydro_output(config, wrf_hydro_site_matches, 
                                                            labelby_pywrdrb_nodes=False, return_df=False)