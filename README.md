

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

---


This script is used to retreive all available NHM data from within the Delaware River Basin and store outputs as CSV files.

The method follows:
1.0 Get the IDs for all segments in the DRB
    1.1 Load the USGS geospatial fabric (GFv1.1) and DRB boundary
    1.2 Clip the GF using the boundary to identify all DRB relevant info.
2.0 Load and extract the NHM data of interest
    2.1 Load the .tar and get file members
    2.2 Extract files of interest
    2.3 Filter the data for DRB relevant values
3.0 Export CSVs



