from arcgis.gis import GIS
from dotenv import load_dotenv
import os
import shutil
import geopandas as gpd
import pandas as pd
import yaml
from datetime import datetime, timezone, timedelta

from arcgis.gis import GIS

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
# load environment variables from .env file
load_dotenv(os.path.join(project_root, ".env"))

with open(os.path.join(project_root, "data_configuration.yaml"), "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

companies_run   = cfg['companies_run']
c1              = cfg['c1']
c2              = cfg['c2']

try:
    credential = GIS(
        os.getenv("ARCGIS_PORTAL_URL"),
        os.getenv("ARCGIS_USERNAME"),
        os.getenv("ARCGIS_PASSWORD")
    )
except Exception as e:
    raise RuntimeError(f"Failed to authenticate to ArcGIS Portal: {e}")

def arcgisGet_sugarcaneGeneric(companies_select, gis):
    print('entering process:', companies_select)
    sugarcane_gdb_path      = cfg['companies'][companies_select]['sugarcane_gdb_path']

    comp_lower = companies_select.lower()
    layer_title =  f"{comp_lower}_sugarcane_generic"

    folder_name = "farm_intelligence_systems"
    target_folder = gis.content.folders.get(folder=folder_name, owner=gis.users.me.username)
    print('target_folder:', target_folder)

    query = f'title:"{layer_title}" AND owner:{gis.users.me.username}'
    selectedLayer = gis.content.search(query=query, item_type="Apache Parquet")[0]

    def item_timestamps(item, tz_offset_hours: int = 7) -> dict:
        """Convert an Item's created/modified epoch-ms fields to readable
        local time (default: Jakarta, UTC+7)."""
        tz = timezone(timedelta(hours=tz_offset_hours))
        return {
            "created": datetime.fromtimestamp(item.created / 1000, tz=tz),
            "modified": datetime.fromtimestamp(item.modified / 1000, tz=tz),
        }
    layerMetaDataSelected = item_timestamps(selectedLayer)

    save_path = os.path.join(os.path.dirname(sugarcane_gdb_path), layer_title)
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

    modified_date = layerMetaDataSelected["modified"].strftime("%Y%m%d")
    layer_name = f'Sugarcane-Raw_{companies_select}_{modified_date}_PT'

    gdf.to_file(
        sugarcane_gdb_path,
        layer=layer_name,
        driver='GPKG'
    )

    # remove temporary file
    os.remove(save_path)
    

# Entery Point
if __name__ == "__main__":
   for i in range(len(companies_run)):
       company_select = companies_run[i]
       arcgisGet_sugarcaneGeneric(companies_select=company_select, gis=credential)
       print(company_select, 'Successfully Processed ......')