from arcgis.gis import GIS
from dotenv import load_dotenv
import os
import shutil
import geopandas as gpd
import pandas as pd
import yaml

from arcgis.gis import GIS

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

# gpkg_gaps_path        = cfg['companies'][companies_select]['gpkg_gaps_planting_path']

try:
    credential = GIS(
        os.getenv("ARCGIS_PORTAL_URL"),
        os.getenv("ARCGIS_USERNAME"),
        os.getenv("ARCGIS_PASSWORD")
    )
except Exception as e:
    raise RuntimeError(f"Failed to authenticate to ArcGIS Portal: {e}")

def arcgisPush_rawPoints():
    folder_name = "farm_intelligence_systems"
    target_folder = gis.content.folders.get(folder=folder_name, owner=gis.users.me.username)
    layer_title = "gpa_sugarcane_generic"
    print('target_folder:', target_folder)

    query = f'title:"{layer_title}" AND owner:{gis.users.me.username}'
    selectedLayer = gis.content.search(query=query, item_type="Apache Parquet")[0]

    save_path=r"D:\00. Geo-AI Apps\automation of gap and weed detection\database\GPA\get_trial.parquet"
    save_dir = os.path.dirname(save_path)
    os.makedirs(save_dir, exist_ok=True)

    downloaded_path = selectedLayer.download(save_path=save_dir)

    if downloaded_path != save_path:
        shutil.move(downloaded_path, save_path)

    print(f"Downloaded '{selectedLayer.title}' ({selectedLayer.type}) to: {save_path}")


    sugarcane_generic = pd.read_parquet(save_path)
    print('sugarcane_generic: ', sugarcane_generic.head())

    # 2. Convert to a GeoDataFrame using points_from_xy
    gdf = gpd.GeoDataFrame(
        sugarcane_generic, 
        geometry=gpd.points_from_xy(sugarcane_generic['x'], sugarcane_generic['y']), 
        crs='EPSG:32754'
    ).drop(columns=['x', 'y'])

    gdf.to_parquet(r"D:\00. Geo-AI Apps\automation of gap and weed detection\database\GPA\get_gdf_trial.parquet")

# Entery Point
if __name__ == "__main__":
   for i in range(len(companies_run)):
       company_select = companies_run[i]
       arcgisPush_gapsDetection(companies_select=company_select, gis=credential)
       print(company_select, 'Successfully Processed ......')