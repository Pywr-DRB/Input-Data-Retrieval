"""
Script for aggregating DRB demands to align with Pywr-DRB nodes. 

Overview:
The DRBC has published water demand data for DRB catchments, but 
these catchments do not align with the pywrdrb node catchments.
In order to provide pywrdrb with demand data, we need to re-aggregate the 
demands such that they align with the pywrdrb node catchment. 

Technical Notes:
- I've left the groundwater processing script, but it is commented out and has never been used in the pywrdrb model (TJA)

Written by Andrew Hamilton in 2022, adapted from Noah Knowles' script for DRB WEAP model.
"""

import os
import pandas as pd
import numpy as np
import geopandas as gpd

from pywrdrb.pywr_drb_node_data import upstream_nodes_dict
from pywrdrb.utils.lists import majorflow_list, reservoir_list

# Directories
from .directories import SPATIAL_DIR, DEMAND_DIR, PYWRDRB_DATA_DIR


def disaggregate_DRBC_demands():
    """
    Disaggregates DRBC water demand data to align with PywrDRB catchments.

    Returns:
        pd.DataFrame: Contains demand data disaggregated to align with PywrDRB catchments.
    """

    ### set seed for consistent results
    np.random.seed(1)

    demand_data_dir = f"{DEMAND_DIR}/"
    DRB_data_dir = f"{SPATIAL_DIR}/"

    ### catchments from model
    g1 = gpd.GeoDataFrame.from_file(f"{DRB_data_dir}node_basin_geometries.shp")

    ### update names to match pywr nodes
    nodes = g1["node"].values
    for i in range(len(nodes)):
        if nodes[i] in reservoir_list:
            nodes[i] = "reservoir_" + nodes[i]
        elif "link_" in nodes[i]:
            pass
        else:
            nodes[i] = "link_" + nodes[i]
    g1["node"] = nodes

    ### subtract upstream catchments from mainstem nodes - note on a few occasions (eg pepacton & its gage), they are too close together and dont recognise a difference,so they disappear from this dataframe.
    for node, upstreams in upstream_nodes_dict.items():
        node_drb = "link_" + node
        for upstream in upstreams:
            if upstream in majorflow_list:
                upstream_drb = "link_" + upstream
            else:
                upstream_drb = "reservoir_" + upstream
            overlay = g1.loc[g1["node"] == node_drb].overlay(
                g1.loc[g1["node"] == upstream_drb], how="difference"
            )
            g1 = g1.loc[g1["node"] != node_drb]
            g1 = pd.concat([g1, overlay])

    g1.reset_index(inplace=True, drop=True)
    g1["idx"] = list(g1.index)

    model_basin_id_name = "node"
    # catchments from DRBC 2021 report
    g2 = gpd.GeoDataFrame.from_file(
        DRB_data_dir + "drb147.shp"
    )  # 147 basins used in report

    g1 = g1.to_crs(g2.crs)
    indx_list = []
    data = []
    for index, model_basin in g1.iterrows():
        for index2, drbc_basin in g2.iterrows():
            if model_basin["geometry"].intersects(drbc_basin["geometry"]):
                intersect_area = (
                    model_basin["geometry"].intersection(drbc_basin["geometry"]).area
                )
                frac_area_model_basin = intersect_area / model_basin["geometry"].area
                frac_area_drbc_basin = intersect_area / drbc_basin["geometry"].area
                indx_list.append((model_basin.node, drbc_basin.BASIN_ID))
                data.append(
                    {
                        "frac_area_model_basin": frac_area_model_basin,
                        "frac_area_drbc_basin": frac_area_drbc_basin,
                    }
                )

    indx = pd.MultiIndex.from_tuples(
        indx_list, names=[model_basin_id_name, "DRBC_BASIN_ID"]
    )
    df_areas = pd.DataFrame(
        data, columns=["frac_area_model_basin", "frac_area_drbc_basin"], index=indx
    )

    # first, load GW and SW for WD and CU for each DB basin and category (2 dataframes: sw and gw; index: db BASIN_ID; column levels: category, WD_or_CU); leave out self-supplied domestic (no gw/sw/designation).
    usecolnames = ["BASIN_ID", "YEAR", "DESIGNATION", "WD_MGD", "CU_MGD"]
    # historical (1990-2018)
    sheetnames = {
        "PWS": "A-1",
        "PWR_THERM": "A-6",
        "PWR_HYDRO": "A-9",
        "IND": "A-11",
        "MIN": "A-14",
        "IRR": "A-17",
        "OTH": "A-22",
    }
    yrbeg, yrend = 2000, 2018  # avg over years from 2000 on

    ##projected (2010-2060)
    # sheetnames = { 'PWS':'A-2',
    #'PWR_THERM':'A-7',
    #'PWR_HYDRO':'A-10',
    #'IND':'A-12',
    #'MIN':'A-15',
    #'IRR':'A-19',  # 18=RCP4.5, 19=RCP8.5
    #'OTH':'A-23'
    # }
    # yrbeg,yrend = 2010,2060

    def mean_over_period(s):
        t = pd.PeriodIndex(
            [
                pd.Period(r)
                for r in s.droplevel(level=0).index.values.astype(int).tolist()
            ]
        )
        s.index = t
        v = s  # comment this and uncomment next line to fill in zeros for missing years
        # v=s.resample('A').asfreq().fillna(0)
        w = v.loc[str(yrbeg) : str(yrend), :].mean()
        return w

    sw_list = []
    # gw_list = []
    for cat in sheetnames:
        sheet = sheetnames[cat]
        df = pd.read_excel(
            demand_data_dir + "DRBCreport_data-release_v2110.xlsx",
            sheet,
            engine="openpyxl",
            usecols=usecolnames,
        )
        df = (
            df.set_index("DESIGNATION", append=True)
            .unstack()
            .swaplevel(1, 0, axis=1)
            .sort_index(axis=1)
        )

        if "SW" in df.columns.levels[0].values:
            sw = (
                df.loc[:, ("SW", slice(None))]
                .droplevel(axis=1, level=0)
                .dropna(subset=["BASIN_ID"])
            )
            sw = sw.groupby(
                ["BASIN_ID", "YEAR"]
            ).sum()  # sum is to aggregate over the Pennsylvania GWPA subbasins
            sw.columns.name = "WD_or_CU"
            sw = pd.concat({cat: sw}, names=["Category"], axis=1)
            sw = sw.groupby("BASIN_ID").apply(mean_over_period)
            sw_list.append(sw)

        # if 'GW' in df.columns.levels[0].values:
        #     gw = df.loc[:,('GW',slice(None))].droplevel(axis=1,level=0).dropna(subset=['BASIN_ID'])
        #     gw = gw.groupby(['BASIN_ID','YEAR']).sum()
        #     gw.columns.name='WD_or_CU'
        #     gw = pd.concat({cat: gw}, names=['Category'],axis=1)
        #     gw = gw.groupby('BASIN_ID').apply(mean_over_period)
        #     gw_list.append(gw)

    # Unclear whether to fill missing years and missing basins with 0. Currently implemented: years no, basins yes. This was based on data. E.g., sometimes a whole decade is missing in a time series-- unlikely to be all zeros. But some basins have, eg, all their demand in gw and no entries for sw, so it makes sense to assume sw=0 for those basins.
    df_sw = pd.concat(sw_list, axis=1).fillna(
        0
    )  # fillna(0) assumes no data at a site for a category means 0 MGD
    # df_gw = pd.concat(gw_list,axis=1).fillna(0)

    # now use frac_area_drbc_basin to calculate weighted sums of sw and gw for model catchments
    model_basin_ids = df_areas.index.get_level_values(level=0).unique()
    sw_list = []
    # gw_list = []
    for model_basin_id in model_basin_ids:
        frac_areas = df_areas.loc[(model_basin_id, slice(None)), :].droplevel(level=0)[
            "frac_area_drbc_basin"
        ]
        sw_model0 = (
            df_sw.reindex(index=frac_areas.index)
            .fillna(0)
            .multiply(frac_areas, axis=0)
            .sum()
        )  # fillna(0) assumes no data at a site for a category means 0 MGD
        sw_model0.name = model_basin_id
        # gw_model0 = df_gw.reindex(index=frac_areas.index).fillna(0).multiply(frac_areas,axis=0).sum()
        # gw_model0.name = model_basin_id
        sw_list.append(sw_model0)
        # gw_list.append(gw_model0)

    # results in MGD
    sw_model = pd.concat(sw_list, axis=1).T
    sw_model[("Total", "CU_MGD")] = sw_model.loc[:, (slice(None), "CU_MGD")].sum(axis=1)
    sw_model[("Total", "WD_MGD")] = sw_model.loc[:, (slice(None), "WD_MGD")].sum(axis=1)
    # gw_model = pd.concat(gw_list,axis=1).T
    # gw_model[('Total','CU_MGD')] = gw_model.loc[:,(slice(None),'CU_MGD')].sum(axis=1)
    # gw_model[('Total','WD_MGD')] = gw_model.loc[:,(slice(None),'WD_MGD')].sum(axis=1)

    ### change columns from multiindex to single index
    sw_model.columns = sw_model.columns.to_flat_index()
    sw_model.columns = [l[0] + "_" + l[1] for l in sw_model.columns]
    # gw_model.columns = gw_model.columns.to_flat_index()
    # gw_model.columns = [l[0] + '_' + l[1] for l in gw_model.columns]

    ### get ratio of consumption to withdrawal
    sw_model["Total_CU_WD_Ratio"] = sw_model["Total_CU_MGD"] / sw_model["Total_WD_MGD"]
    sw_model["Total_CU_WD_Ratio"].loc[np.isnan(sw_model["Total_CU_WD_Ratio"])] = 0.0
    # gw_model['Total_CU_WD_Ratio'] = gw_model['Total_CU_MGD'] / gw_model['Total_WD_MGD']
    # gw_model['Total_CU_WD_Ratio'].loc[np.isnan(gw_model['Total_CU_WD_Ratio'])] = 0.

    ### Set demands to zero in cases where we don't have data either because no USGS gage to use as pour point(merrill creek),
    ###    or because the gage is too close to reservoir to deliniate marginal catchment.
    for reservoir in reservoir_list:
        if f"reservoir_{reservoir}" not in sw_model.index:
            sw_model = pd.concat(
                [
                    sw_model,
                    pd.DataFrame(
                        {k: 0.0 for k in sw_model.columns},
                        index=[f"reservoir_{reservoir}"],
                    ),
                ]
            )
    for majorflow in majorflow_list:
        if f"link_{majorflow}" not in sw_model.index:
            sw_model = pd.concat(
                [
                    sw_model,
                    pd.DataFrame(
                        {k: 0.0 for k in sw_model.columns}, index=[f"link_{majorflow}"]
                    ),
                ]
            )
    sw_model.loc["reservoir_merrillCreek", :] = np.zeros(sw_model.shape[1])
    # for reservoir in reservoir_list:
    #     if f'reservoir_{reservoir}' not in gw_model.index:
    #         gw_model = gw_model.append(pd.DataFrame({k: 0. for k in gw_model.columns}, index=[f'reservoir_{reservoir}']))
    # for majorflow in majorflow_list:
    #     if f'link_{majorflow}' not in gw_model.index:
    #         gw_model = gw_model.append(pd.DataFrame({k: 0. for k in gw_model.columns}, index=[f'link_{majorflow}']))
    # gw_model.loc['reservoir_merrillCreek', :] = np.zeros(gw_model.shape[1])

    # Save to CSV
    sw_model.to_csv(
        f"{PYWRDRB_DATA_DIR}sw_avg_wateruse_pywrdrb_catchments_mgd.csv", 
        index_label="node"
    )


if __name__ == "__main__":
    
    print("Re-aggregating DRBC demand data to align with pywrdrb node catchments...")
    
    try:
        disaggregate_DRBC_demands()
    except Exception as e:
        print(f"Error during demand re-aggregation:\n{e}")
        raise
    
    print("Done; new demand data saved to src_pywrdrb_data/ folder.")