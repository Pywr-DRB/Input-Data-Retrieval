
## Overview

This repo is used to prepare and store streamflow data which is used as input to the Pywr-DRB model.

Data which is prepared & stored here includes:
- USGS gauge streamflow data which is retrieved from the NWIS.
- NHMv1.0 (NHM-PRMS) modeled streamflow data which is extracted from a CONUS scale dataset.
- NWMv2.1 modeled streamflow which is extracted from a CONUS scale dataset.
- Scaled gauge streamflow using NHMv1.0 and NWM2.1 to predict gauge-catchment scaling relationships at some reservoirs in the DRB.

These data are stored in the `datasets/` folder under within their respective `/USGS/`, `/NHMv10/`, and `/NWMv21/` subdirectories. 

| Dataset | Filename | Description | 
| --- | --- | --- |
| USGS | `drb_all_usgs_metadata.csv` | Metadata for all gauges in the DRB from NWIS query which includes site number, lat, long, comid, etc. | 
| USGS | `drb_unmanaged_usgs_metadata.csv` | Metadata for just those gauges deemed to be 'unmanaged', based on NLDI upstream storage and dam characteristic data. | 
| USGS | `streamflow_daily_usgs_cms.csv` | Daily streamflow at USGS gauges in the DRB. Units in CMS. These are later used by Pywr-DRB.|
| NHMv10 |  `hdf/drb_seg_outflow_mgd.hdf5` | All NHMv1.0 modeled segment outflows in the DRB in HDF5 format. | 
| NHMv10 | `csv/streamflow_daily_nhmv10_mgd.csv` | NHMv1.0 modeled streamflows which are used as Pywr-DRB inputs. | 
| NWMv21 | `nwmv21_unmanaged_gauge_metadata.csv` | Metadata for USGS gauges that are modeled in NWM. Includes site number, comid, lat, and long. | 
| NWMv21 | `nwmv21_unmanaged_gauge_streamflow_daily.csv` | NWM modeled flows at some USGS gauge locations. This is used in the historic streamflow reconstruction (DRB-Historic-Reconstruction). | 
| NWMv21 | `streamflow_daily_nwmv21_mgd.csv` | NWM modeled flows at gauges, segments, and lake inflows. This was provided by NCAR collaborators. | 
| Hybrid | `USGS/scaled_inflows_nhmv10.csv` | Reservoir inflow timeseries at some DRB reservoirs which are generated as the scaled aggregate sum of inflow gauges into that reservoir. Scaling is based on a linear regression of NHM modeled flow at the catchment outlet relative to the NHM modeled flow at the observed gauges. | 
| Hybrid | `USGS/scaled_inflows_nhmv10` | Same as above, with the scaling based on NWM modeled streamflows. | 


### Data Processing Scripts

The processing used to generate the above-described datasets can be replicated using this scripts in the root folder of this repo.   

Before getting started, you should modify the paths contained in the `directories.py` file.  These paths should point to folders containing the original data source files, listed in the Data Sources section of this README.

At the top of each script is a list of necessary files that need to be available in the specified directory. 

- `retireve_usgs_data.py`
    - This script will use the NWIS to retrieve metadata and daily streamflow data at USGS gauges in the DRB. 

---

## Data sources

**National Hydrologic Model Precipitation-Runoff Modeling System (NHM-PRMS; NHMv1.0) Daily Streamflow (92GB):**
Hay, L.E., and LaFontaine, J.H., 2020, Application of the National Hydrologic Model Infrastructure with the Precipitation-Runoff Modeling System (NHM-PRMS),1980-2016, Daymet Version 3 calibration: U.S. Geological Survey data release, https://doi.org/10.5066/P9PGZE0S. [Download here: ScienceBase](https://www.sciencebase.gov/catalog/item/5d826f6ae4b0c4f70d05913f)
- `byHRU_musk_obs.tar`


**National Water Model V2.1 (NWMv2.1) NWIS Retrospective (2GB):**
Blodgett, D.L., 2022, National Water Model V2.1 retrospective for selected NWIS gage locations, (1979-2020): U.S. Geological Survey data release, https://doi.org/10.5066/P9K5BEJG. [Download here: ScienceBase](https://www.sciencebase.gov/catalog/item/612e264ed34e40dd9c091228)
- `nwmv21_nwis.nc`


**Geospatial Fabric (GFv1.1) for the NHM (1GB):**
Bock, A.E, Santiago,M., Wieczorek, M.E., Foks, S.S., Norton, P.A., and Lombard, M.A., 2020, Geospatial Fabric for National Hydrologic Modeling, version 1.1 (ver. 3.0, November 2021): U.S. Geological Survey data release, https://doi.org/10.5066/P971JAGF.
[Download here: ScienceBase](https://www.sciencebase.gov/catalog/item/5e29d1a0e4b0a79317cf7f63)
- `GFv1.1.gdb.zip`
- `nhm_to_GFv1.1_HRU.csv`
- `nhm_to_GFv1.1_SEG.csv`


Point of Interest IDs (`poi_gage_segment.csv` and `poi_gage_id.csv`) were retrieved from: 
https://github.com/nhm-params-v10-usgs/paramdb_v10_daymet_CONUS

